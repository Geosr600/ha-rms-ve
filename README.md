# ⚡ RMS VE F1ATB – Home Assistant Integration

Intégration Home Assistant pour piloter une borne de recharge VE RMS (H3rv3 / Pedro) via API REST locale.

> 🔌 Contrôle direct • 🏠 Local • ⚡ Compatible surplus photovoltaïque

---

## 🚀 Pourquoi cette intégration ?

Cette intégration permet d’intégrer votre borne RMS VE directement dans Home Assistant pour :

* 🔄 Automatiser la recharge
* ☀️ Exploiter le surplus photovoltaïque
* 🎯 Ajuster finement le courant de charge
* 🧠 Intégrer la borne dans vos scénarios énergétiques

⚠️ **Important :**
Cette intégration fournit les commandes.
La logique énergétique reste gérée par le RMS F1ATB.

---

## ⚙️ Fonctionnalités

### 🔌 Contrôle de la borne

* Modes disponibles :

  * Automatique
  * Manuel
  * Semi-automatique
  * Heures creuses
  * Arrêt

### ⚡ Gestion de la charge

* Réglage du courant de charge
* Pilotage en temps réel via Home Assistant

### 📊 Supervision

* État de la liaison VE (A/B/C/D/F)
* Mode actif
* Données API (`/data`)

---

## 🏠 Intégration Home Assistant

L’intégration ajoute :

### Entités

* Mode de fonctionnement
* Courant de charge
* État de la borne

### Services

* Changement de mode
* Réglage du courant

---

## 🧱 Architecture

* Communication locale via HTTP (API REST)
* ESP32 RMS VE
* Compatible :

  * Version H3rv3
  * Version Pedro

---

## ⚠️ Limites

* ❌ Pas de logique intelligente intégrée
* ❌ Dépend de l’API RMS VE
* ❌ Nécessite une borne fonctionnelle sur le réseau local

---

## 📚 Projet RMS VE

Le RMS VE est une solution open-source basée sur le système RMS F1ATB.

### Fonctionnalités principales :

* ☀️ Gestion du surplus photovoltaïque
* 📈 Suivi temps réel de la charge
* ⏱️ Programmation heures creuses
* 🖥️ Interface web intégrée
* 📟 Support écran OLED

📖 Documentation :
https://acloud9.zaclys.com/index.php/s/73zkjdsWS4FFF32

💬 Présentation :
https://f1atb.fr/forum_f1atb/thread-1717.html

---

## 👥 Crédits

Projet RMS VE :

* Cmichel
* H3rv3
* Rakibou

Intégration Home Assistant :

* GeoSR

---

## ⭐ Support

Si cette intégration vous est utile :
👉 pensez à laisser une ⭐ sur GitHub
