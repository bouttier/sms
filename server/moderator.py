# -*- coding: utf-8 -*-

from threading import Thread
from settings import MOD_PORT
import socket
import select
import queue
import os
from queue import Queue
from collections import deque


class Moderator(Thread):
    
    def __init__(self, send):
        
        Thread.__init__(self)
        self.daemon = True
        self.send = send
        self.pipe_r, self.pipe_w = os.pipe()
        self.sms = Queue() # sms en attente de modération
        self.init_server()

    def init_server(self):
        # Création serveur
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        self.server.bind( ('', MOD_PORT) )
        self.server.listen(5)
        print('started moderation server on port', MOD_PORT)

        self.outputs = []
        self.free = deque() # modérateur en attente de sms
        self.awaiting = {} # sms attribué à un modérateur
        self.queues = {} # queues d’envoit

    def moderate(self, phone, message):
        ''' fonction appelé lorsqu’un nouveau sms est à modérer '''
        self.sms.put((phone, message), True, None)
        os.write(self.pipe_w, bytes('\0', 'UTF-8')) # Réveille du select
        
    def run(self):
        while self.server:
            readable, writable, exceptional = select.select(
                    [self.server, self.pipe_r] + list(self.awaiting.keys()), # input
                    self.outputs, # output
                    [self.server]) # error

            for s in readable:
                if s is self.server: # Connexion entrante
                    modo, address = self.server.accept()
                    modo.setblocking(0)
                    self.awaiting[modo] = None
                    self.free.appendleft(modo)
                    self.queues[modo] = Queue()

                elif s is self.pipe_r: # Nouveau sms à modérer
                    os.read(self.pipe_r, 1)

                else: # Modo
                    data = s.recv(1024)
                    if data:
                        if self.awaiting[s]: # Modération
                            response = data.strip().decode('UTF-8')
                            if response == "o" or response == "":
                                self.send(self.awaiting[s][0],
                                        self.awaiting[s][1])
                                self.awaiting[s] = None
                                self.free.appendleft(s)
                            elif response == "n":
                                self.awaiting[s] = None
                                self.free.appendleft(s)
                            else:
                                self.queues[s].put(
                                    bytes("Veuillez répondre par 'o' ou 'n'\n", 'UTF-8'))
                                if s not in self.outputs:
                                    self.outputs.append(s)
                        else: # Le mec dit de la merde
                            pass
                    else: # Déconnexion
                        if s in self.outputs:
                            self.outputs.remove(s)
                        if s in self.free:
                            self.free.remove(s)
                        if self.awaiting[s]:
                            self.sms.put(self.awaiting[s])
                        del self.awaiting[s]
                        s.close()

            for s in writable: # Il est possible d’envoyer des données
                try:
                    next_msg = self.queues[s].get_nowait()
                    s.send(next_msg)
                except queue.Empty: # Envoit terminé
                    self.outputs.remove(s)
                except socket.error:
                    if s in self.outputs:
                        self.outputs.remove(s)
                    if s in self.free:
                        self.free.remove(s)
                    if self.awaiting[s]:
                        self.sms.put(self.awaiting[s])
                    del self.awaiting[s]
                    s.close()


            for s in exceptional: # Serveur planté
                for client in clients:
                    if self.awaiting[client]:
                        self.sms.put(self.awaiting[client])
                    client.close()
                s.close()
                self.init_server() # Reboot du serveur
            
            while not self.sms.empty(): # Il reste des sms à modérer
                try:
                    modo = self.free.pop()
                except IndexError: # Plus de modérateur disponible
                    break
                else:
                    sms = self.sms.get()
                    self.awaiting[modo] = sms
                    self.queues[modo].put(bytes("Voulez-vous accepter ce"
                        + " message ? [o/n]\n[%s] %s\n" %sms, 'UTF-8'))
                    self.outputs.append(modo)
