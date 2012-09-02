# -*- coding: utf-8 -*-

from threading import Thread
from settings import MOD_PORT
import socket
import select
import queue
import os
from queue import Queue


class Moderator(Thread):
    
    def __init__(self, send):
        
        Thread.__init__(self) # Constructeur de la classe parente
        self.daemon = True # Ne pas attendre la fin du thread pour quitter

        # Création de la socket
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Option reuseaddr (permet de réutiliser l’adresse sans délai de 1 min)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Socket non bloquante, on va utiliser select
        self.server.setblocking(0)
        # On bind la socket en écoute de toutes les adresse
        self.server.bind( ('', MOD_PORT) )
        print('started moderation server on port', MOD_PORT)
        # Définie le nombre maximal de connexion attendant d’être acceptées
        self.server.listen(5)
        # Création d’un pipe, pipe_w est l’entrée et pipe_r la sortie
        self.pipe_r, self.pipe_w = os.pipe()

        self.clients = [] # Pour les clients
        self.outputs = [] # Pour les clients avec des données en cours d’envoit
        # Message en cours d’envoit vers les clients
        # Les queues devront contenir des données binaire
        self.message_queues = {}
        # Les messages en cours de modération
        self.moderation = {}
        # La fonction pour les messages accepté
        self.send = send
        # La queue des messages à modérer
        self.queue = Queue()

    ''' Méthode appelé lorsqu’un sms doit être envoyé vers les clients '''
    def moderate(self, phone, message):
        self.queue.put((phone, message), True, None)
        os.write(self.pipe_w, bytes('\0', 'UTF-8'))
        
    ''' Méthode lancé par la fonction start() hérité de la classe Thread '''
    def run(self):
        while self.server: # On s’arrête si le serveur est cassé
            readable, writable, exceptional = select.select(
                    # On écoute les clients, le serveur (connexions entrantes),
                    # et pipe_r qui permet de réveiller le select lorsque l’on
                    # veut le relancer avec de nouveaux masques.
                    [self.server, self.pipe_r] + self.clients, # input
                    self.outputs, # output
                    [self.server]) # error

            for s in readable:
                if s is self.server: # Connexion entrante
                    client, address = self.server.accept() # Acceptation
                    client.setblocking(0) # Socket non bloquante (select)
                    self.clients.append(client) # On rajoute dans les clients
                    self.message_queues[client] = queue.Queue() # Queue dédié

                elif s is self.pipe_r: # Utilisé pour réveiller select
                    # Il faut consommer le caratère pour que cela continue de
                    # marcher.
                    os.read(self.pipe_r, 1)

                else: # Client
                    data = s.recv(1024)
                    if data:
                        if s in self.moderation.keys():
                            response = data.strip().decode('UTF-8')
                            if response == "o":
                                phone, message = self.moderation[s]
                                self.send(phone, message)
                                del self.moderation[s]
                            elif response == "n":
                                del self.moderation[s]
                            else:
                                # On rajoute notre message dans la queue d’envoit
                                self.message_queues[s].put(
                                    bytes("Veuillez répondre par 'o' ou 'n'\n", 'UTF-8'))
                                if s not in self.outputs:
                                    self.outputs.append(s)
                        else: # le mec dit de la merde
                            pass
                    else: # Pas de données à lire
                        # Cela signifie que le client à fermer la connexion
                        self.clients.remove(s)
                        if s in self.outputs:
                            self.outputs.remove(s)
                        s.close()
                        if s in self.message_queues.keys():
                            del self.message_queues[s]
                        if s in self.moderation.keys():
                            # on remet le message dans la queue de modération
                            self.queue.put(self.moderation[s])
                            del self.moderation[s]

            for s in writable: # Il est possible d’envoyer des données
                try:
                    # Récupération des prochaines données à envoyer
                    next_msg = self.message_queues[s].get_nowait()
                except queue.Empty:
                    # Plus rien à envoyer, plus besoin de surveiller les
                    # possibilitées d’envoit vers ce client
                    self.outputs.remove(s)
                else:
                    s.send(next_msg) # envoit

            for s in exceptional: # Erreur avec ce client, déconnexion
                self.clients.remove(s)
                if s in self.outputs:
                    self.outputs.remove(s)
                s.close()
                if s in self.message_queues.keys():
                    del self.message_queues[s]
                if s in self.moderation.keys():
                    del self.moderation[s]
        
            for s in self.clients: # Pour chaque client
                if s not in self.moderation: # qui ne modère rien
                    try:
                        sms = self.queue.get_nowait()
                    except queue.Empty: # empty queue
                        break
                    else:
                        self.message_queues[s].put(bytes("Voulez-vous accepter ce"
                            + " message ? [o/n]\n[%s] %s\n" %sms, 'UTF-8'))
                        self.outputs.append(s)
                        self.moderation[s] = sms
