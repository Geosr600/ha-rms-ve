# RMS VE – Home Assistant Integration

Intégration Home Assistant permettant de piloter une borne de recharge VE RMS (version H3rv3 / Pedro) via API REST locale.

> ⚠️ Cette intégration est une interface de commande.  
> Elle ne gère pas la logique énergétique : celle-ci est assurée par le RMS F1ATB.

---

## 🎯 Objectif

Cette intégration expose les commandes et états de la borne VE RMS dans Home Assistant afin de :

- Contrôler les modes de fonctionnement
- Ajuster le courant de charge
- Superviser l’état de la borne
- Intégrer la recharge dans vos automatisations Home Assistant

---

## ⚙️ Fonctionnalités

- Changement de mode :
  - Automatique
  - Manuel
  - Semi-automatique
  - Heures creuses
  - Arrêt

- Réglage du courant de charge (mode manuel)

- Lecture des états :
  - État de la liaison VE (A/B/C/D/F)
  - Mode actif
  - Données remontées via API `/data`

- Intégration simple via REST (locale, sans cloud)

---

## 🧱 Architecture

- Communication directe avec la borne RMS VE via API HTTP
- Basée sur le firmware RMS VE (ESP32)
- Compatible avec les versions :
  - H3rv3 (carte dédiée)
  - Pedro (ESP32 + Arduino)

---

## 🏠 Intégration Home Assistant

L’intégration crée :

- Des entités pour :
  - Le mode
  - Le courant
  - L’état de la borne

- Des services pour :
  - Changer le mode
  - Ajuster le courant

---

## ⚠️ Limites

- Pas de logique embarquée (pilotage intelligent à faire côté HA ou RMS)
- Dépend de la disponibilité de l’API RMS VE
- Nécessite une borne RMS fonctionnelle sur le réseau local

---

## 📚 Projet RMS VE

Le projet RMS VE est une station de recharge open-source développée autour du système RMS F1ATB.

### Caractéristiques principales :

- Gestion dynamique du surplus photovoltaïque
- Interface web complète intégrée au RMS
- Modes avancés (auto, semi-auto, heures creuses)
- Suivi temps réel de la charge et de l’énergie
- Support écran OLED (optionnel)

📖 Documentation complète :  
https://acloud9.zaclys.com/index.php/s/73zkjdsWS4FFF32

Présentation du projet :  
https://f1atb.fr/forum_f1atb/thread-1717.html

---

## 👥 Crédits

Projet RMS VE développé par :
- Cmichel
- H3rv3
- Rakibou

Intégration Home Assistant :  
- GeoSR
