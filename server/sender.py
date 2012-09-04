# -*- coding: utf-8 -*-

from threading import Thread
from settings import OUTPUT_PORT
import socket
import select
import queue
import os


class Sender(Thread):
    
    def __init__(self):
        
        Thread.__init__(self)
        self.daemon = True

        self.pipe_r, self.pipe_w = os.pipe()
        self.init_server()
        

    def init_server(self):
        # Création serveur
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(0)
        self.server.bind( ('', OUTPUT_PORT) )
        print('started output server on port', OUTPUT_PORT)
        self.server.listen(5)
        
        self.clients = []
        self.outputs = []
        self.message_queues = {}

    def send(self, phone, message):
        ''' Méthode appelé lorsqu’un sms doit être envoyé vers les clients '''
        for s in self.clients: # Pour chaque client
            self.message_queues[s].put(bytes("[%s] %s\n" %(phone, message),
                'UTF-8'))
        self.outputs.extend(self.clients)
        os.write(self.pipe_w, bytes('\0', 'UTF-8')) # Réveille du select
        
    def run(self):
        while self.server:
            readable, writable, exceptional = select.select(
                    [self.server, self.pipe_r] + self.clients, # input
                    self.outputs, # output
                    [self.server]) # error

            for s in readable:
                if s is self.server: # Connexion entrante
                    client, address = self.server.accept()
                    client.setblocking(0)
                    self.clients.append(client)
                    self.message_queues[client] = queue.Queue()

                elif s is self.pipe_r: # Nouvelle valeurs de self.outputs
                    os.read(self.pipe_r, 1)

                else: # Client
                    try:    
                        data = s.recv(1024)
                    except socket.error:
                        self.clients.remove(s)
                        if s in self.outputs:
                            self.outputs.remove(s)
                        s.close()
                        del self.message_queues[s]
                    else:
                        if data:
                            self.message_queues[s].put(
                                bytes('Désolé, je n’écoute pas\n', 'UTF-8'))
                            if s not in self.outputs:
                                self.outputs.append(s)
                        else: # Déconnexion
                            self.clients.remove(s)
                            if s in self.outputs:
                                self.outputs.remove(s)
                            s.close()
                            del self.message_queues[s]

            for s in writable: # Il est possible d’envoyer des données
                try:
                    next_msg = self.message_queues[s].get_nowait()
                except queue.Empty: # tous a été envoyé
                    self.outputs.remove(s)
                else:
                    s.send(next_msg)

            for s in exceptional: # Server planté
                for client in self.clients:
                    client.close()
                s.close()
                self.init_server() # reboot du server
