#!/usr/bin/env python2
# -*- coding: utf8 -*-

## Récupère les noms associés aux numéros de téléphone
## enregistrés dans le LDAP

import ldap
import getpass
import shutil
import cPickle

FILENAME = 'phonedump'

conn = ldap.initialize('ldap://ldapmaster')

## login inp-net
login = raw_input("Login INP-net : ")
mdp = getpass.getpass("Mot de passe pour %s : " %login)
print("")
login_ldap = "uid="+login+",ou=people,o=n7,dc=etu-inpt,dc=fr"
conn.bind_s(login_ldap, mdp) ## connexion

## rechercher
attr = ['mobile', 'cn'] ## attributs à afficher
s = conn.search_s(base='o=n7,dc=etu-inpt,dc=fr',
                  scope=ldap.SCOPE_SUBTREE,
                  filterstr='objectClass=Eleve',
                  attrlist=attr)

d = {}
for dn,dico in s:
    try:
        mobile = dico['mobile'][0].decode('UTF-8')
        name = dico['cn'][0].decode('UTF-8')
        d[mobile] = name
    except KeyError:
        pass


## ajout des éléments du dico à la fin du fichier
with open(FILENAME, 'w') as f:
    cPickle.dump(d, f)


## déconnexion
conn.unbind_s()
