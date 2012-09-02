#!/usr/bin/env python2
# -*- coding: utf8 -*-

import chardet
import pygame
import sys
import os
import socket
import re
from time import sleep
from pygame.time import get_ticks
from pygame.display import update as update_display
from threading import Thread
from Queue import Queue, Empty
import cPickle
import settings


class RecvSMS(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        
        self.queue = queue
        self.daemon = True

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((settings.SERVER, settings.PORT))
            
    def run(self):
        while True:
            receive = self.socket.recv(1024).rstrip("\r\n").decode('UTF-8')
            match = re.match( r'\[[+]?(\d*)\] (.*)', receive, re.M)
            if match:
                self.queue.put(match.group(2))


class BandeauDefilant(object):
    def __init__(self, ecran, fonte, zone_aff):
        self.texte = fonte.render(settings.BANNER, True, settings.COLOR_BANNER, (0, 0, 0))
        self.long_texte = self.texte.get_width()
        if settings.POSITION == "bottom":
            self.y = zone_aff.bottom - self.texte.get_height()
        else:
            self.y = zone_aff.top
        self.maj_rect = pygame.Rect(zone_aff.left, self.y, zone_aff.width, self.texte.get_height())
        self.ecran = ecran
        self.intervalle = self.long_texte + settings.BANNER_SPACING
        self.espacement_rect = pygame.Rect(0, self.y, settings.BANNER_SPACING, self.texte.get_height())
        self.decalage_x = zone_aff.left

    def afficher(self):
        x = self.decalage_x - (get_ticks() // settings.SPEED) % self.intervalle
        self.ecran.blit(self.texte, (x, self.y))
        self.espacement_rect.x = x + self.long_texte
        self.ecran.fill((0, 0, 0), self.espacement_rect)
        self.ecran.blit(self.texte, (x + self.intervalle, self.y))
        return self.maj_rect

def calibrer_ecran(ecran):
    print "Calibration de la zone d’affichage :"
    print "Vérifiez que le rectangle blanc est entièrement visible à l’écran."
    print "Si ce n’est pas le cas, ajustez ses dimensions."
    print "Utilisez ZQSD pour déplacer le coin haut gauche du rectangle, les touches "
    print "fléchées pour le coin bas droite, et Entrée pour valider la zone."
    
    rect = ecran.get_rect()
    pygame.key.set_repeat(500, 50)
    
    while True:
        ecran.fill((0, 0, 0))
        pygame.draw.rect(ecran, (255, 255, 255), rect, 2)
        pygame.display.flip()
        event = pygame.event.wait()
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_q, pygame.K_u] and rect.left > 0:
                rect.left -= 1
                rect.width += 1
            elif event.key in [pygame.K_z, pygame.K_p] and rect.top > 0:
                rect.top -= 1
                rect.height += 1
            elif event.key in [pygame.K_d, pygame.K_e] and rect.width > 100:
                rect.left += 1
                rect.width -= 1
            elif event.key in [pygame.K_s, pygame.K_i] and rect.height > 100:
                rect.top += 1
                rect.height -= 1
            elif event.key == pygame.K_LEFT and rect.width > 100:
                rect.width -= 1
            elif event.key == pygame.K_UP and rect.height > 100:
                rect.height -= 1
            elif event.key == pygame.K_RIGHT and rect.right < ecran.get_width():
                rect.width += 1
            elif event.key == pygame.K_DOWN and rect.bottom < ecran.get_height():
                rect.height += 1
            elif event.scancode == 36:
                break
    
    ecran.fill((0, 0, 0, 255), ecran.get_rect())
    pygame.display.flip()
    return rect

def run():
    global continuer

    pygame.init()

    ecran = pygame.display.set_mode(settings.RESOLUTION, pygame.NOFRAME)
    rect = ecran.get_rect()
    rect.move_ip(500, 0)

    pygame.mouse.set_visible(0)

    zone_aff = calibrer_ecran(ecran)
    ecran.set_clip(zone_aff)

    if settings.FONT[-4:] == '.ttf':
        fonte = pygame.font.Font(settings.FONT, settings.FONT_SIZE)
        fonte.set_bold(settings.FONT_BOLD) 
    else:
        fonte = pygame.font.SysFont(FONTE, TAILLE_FONTE, bold=FONTE_GRAS)

    haut_fonte = fonte.size(u"ÉÇp")[1] + 5
    nb_lignes = zone_aff.height // haut_fonte - 1

    if settings.POSITION == "bottom":
        aff_rect = pygame.Rect(zone_aff.left, zone_aff.top + (nb_lignes - 1) * haut_fonte, zone_aff.width, haut_fonte)
    else: 
        aff_rect = pygame.Rect(zone_aff.left, zone_aff.top + nb_lignes * haut_fonte, zone_aff.width, haut_fonte)
    decale_rect = pygame.Rect(0, -haut_fonte, settings.RESOLUTION[0], settings.RESOLUTION[1])

    bandeau = BandeauDefilant(ecran, fonte, zone_aff)
    nettoie_bas = bandeau.afficher()

    horloge_fps = pygame.time.Clock()
    
    queue = Queue()

    RecvSMS(queue).start()

    continuer = True
    switch_color = True
    while continuer:
        pygame.event.clear()
        try:
            message = queue.get_nowait()
            if switch_color:
		        color = settings.COLOR_1
            else:
		        color = settings.COLOR_2
            switch_color = not(switch_color)
        except Empty:
            update_display(bandeau.afficher())
            horloge_fps.tick(settings.FPS_MAX)
            continue
       
        message.replace("\r", "")
        for msg_ligne in message.split("\n"):
            mots = msg_ligne.split(" ")
            while mots:
                ligne_act = None
                while mots:
                    if ligne_act == None:
                        ligne_nouv = mots[0]
                    else:
                        ligne_nouv = ligne_act + " " + mots[0]
                    
                    if fonte.size(ligne_nouv)[0] < aff_rect.width:
                        ligne_act = ligne_nouv
                        mots.pop(0)
                    elif not ligne_act: # Premier mot, et il ne rentre pas !
                        mot_long = mots[0]
                        pos = 1
                        while fonte.size(mot_long[0:pos])[0] < aff_rect.width:
                            pos += 1
                        ligne_act = mot_long[0:pos - 1]
                        mots[0] = mot_long[pos - 1:]
                        break
                    else:
                        break
                
                if ligne_act == None:
                    ligne_act = ""
                
                ecran.fill((0, 0, 0, 255), nettoie_bas)
                ecran.blit(ecran, decale_rect)
                ecran.fill((0, 0, 0, 255), aff_rect)
                for i in xrange(0, len(ligne_act) + 1):
                    surface = fonte.render(ligne_act[0:i], True, color, (0, 0, 0))
                    ecran.blit(surface, aff_rect)
                    if i == 0:
                        bandeau.afficher()
                        pygame.display.flip()
                    else:
                        update_display([aff_rect, bandeau.afficher()])
                    sleep(0.025)

if __name__ == "__main__":
    run()
