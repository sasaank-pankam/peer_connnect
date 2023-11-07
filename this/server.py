import socket as soc
import threading
import select
from . import object as obj
import threading as td
import resources.resources as re


def get_local_ip_address():
    try:
        s = soc.socket(soc.AF_INET, soc.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))

        local_ip_address = s.getsockname()[0]
        s.close()

        return local_ip_address
    except Exception as e:
        return str(e)


def send_name(client: soc.socket, name: str):
    send_name = name.encode()
    send_name += b' ' * (64 - len(send_name))
    client.send(send_name)


def connectPeers(web_socket, name) -> dict[obj.handleSocket]:
    lis = {}  # list of peer sockets

    print('Connecting to the peers')
    with re.locks['server_given_list']:
        if re.server_given_list:
            for addr in re.server_given_list:
                peer = soc.socket(soc.AF_INET, soc.SOCK_STREAM)
                try:
                    peer.connect((addr, 7070))
                    send_name(peer, name)

                    lis[addr[0]] = obj.handleSocket(peer, addr, web_socket, name)
                    print(f'Connected to {addr}')
                except Exception as e:
                    print(f'Cannot able to connect to {addr} due to {e.__cause__} ')
                    continue
    return lis


def managePeers(web_socket, name):
    peers = connectPeers(web_socket, name)

    threads = [td.Thread(target=peers[x].receiveSomething) for x in peers]

    for i in threads:
        i.start()

    with re.locks['connected_sockets']:
        re.connected_sockets.update(peers)

    with re.locks['threads_of_connected_peers']:
        re.threads_of_connected_peers.update(threads)


def acceptPeers(server: soc.socket, web_socket, name, exit_event: threading.Event):
    server.listen()
    print(f'Listening for connections at {server.getsockname()} ')

    while not exit_event.is_set():
        readable, _, _ = select.select([server], [], [], 0.001)

        if server in readable:
            new_client, new_client_address = server.accept()
            print(f'Got a new peer with address {new_client_address}')
            send_name(new_client, name)

            with re.locks['connected_sockets']:
                re.connected_sockets[new_client_address] = (
                    peer := obj.handleSocket(new_client, new_client_address, web_socket, name))

            with re.locks['threads_of_connected_peers']:
                re.threads_of_connected_peers.add(peer := td.Thread(target=peer.receiveSomething))
            peer.start()

        else:
            continue


def makeServer(web_socket, name, exit_event) -> tuple[soc.socket, td.Thread]:
    server_ip = get_local_ip_address()
    server_port = 7070

    print(server_ip, server_port)

    this_server_socket = soc.socket(soc.AF_INET, soc.SOCK_STREAM)
    this_server_socket.bind((server_ip, server_port))
    t1 = td.Thread(target=acceptPeers, args=[this_server_socket, web_socket, name, exit_event])
    t1.start()

    return this_server_socket, t1
