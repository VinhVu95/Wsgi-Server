###########################################################################
# Concurrent server                                                       #
#                                                                         #
# Tested with Python 2.7.9 & Python 3.4 on Ubuntu 14.04 & Mac OS X        #
#                                                                         #
# - Child process sleeps for 60 seconds after handling a client's request #
# - Parent and child processes close duplicate descriptors                #
#                                                                         #
###########################################################################
import os
import socket
import time
import signal
import errno

SERVER_ADDRESS = (HOST, PORT) = '', 8887
REQUEST_QUEUE_SIZE = 5


def grim_reaper(signum, frame):
    pid, status = os.wait()
    print(
        'Child {pid} terminated with status {status}'.format(
            pid=pid, status=status
        )
    )


def grim_reaper_2(signum, frame):
    while True:
        try:
            pid, status = os.waitpid(
                -1,         # Wait for any child process
                os.WNOHANG  # Do not block and return EWOULDBLOCK error
            )
        except OSError:
            return

        if pid == 0: # No more Zombies
            return


def handle_request(client_connection):
    request = client_connection.recv(1024)
    print(request.decode())
    #print(
    #    'Child PID: {pid}. Parent PID {ppid}'.format(
    #        pid=os.getpid(),
    #        ppid=os.getppid(),
    #    )
    #)
    #print(request.decode())
    http_response = b"""\
    HTTP/1.1 200 OK

    Hello, World!
    """
    client_connection.sendall(http_response)
    # sleep to allow the parent to loop over to 'accept' and block there
    time.sleep(3)


def serve_forever():
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(SERVER_ADDRESS)
    listen_socket.listen(REQUEST_QUEUE_SIZE)
    print('Serving HTTP on port {port} ...'.format(port=PORT))
    #print('Parent PID (PPID): {pid}\n'.format(pid=os.getpid()))

    # grim_reaper add signal handler for 1 child process while grim_reaper_2 add event queue for multiple processes
    signal.signal(signal.SIGCHLD, grim_reaper_2)

    clients = []
    while True:
        try:
            client_connection, client_address = listen_socket.accept()
        except IOError as e:
            code, msg = e.args
            # restart 'accept' if it was interrupted
            if code == errno.EINTR:
                print('Ignore EINTR error when SIGCHILD interrupt "accept" listen socket')
                continue
            else:
                raise

        clients.append(client_connection)
        pid = os.fork()
        if pid == 0:  # child process
            listen_socket.close()  # close child copy because child doesn't care about accepting new client connection
            handle_request(client_connection)
            client_connection.close()
            os._exit(0)  # child exits here
        else:  # parent process
            client_connection.close()  # close parent copy (file descriptor ref for client socket is now 1)
            # and loop over
            # print(len(clients))

if __name__ == '__main__':
    serve_forever()