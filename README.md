# RMS VE - v0.2.0

## Installation
1. Copier `custom_components/ve_router` dans `/config/custom_components/`
2. Redémarrer Home Assistant
3. Ajouter l'intégration `RMS VE`


## Toutes les informations disponibles dans l'éditeur
- Mode de fonctionnement
- Régulation auto VE disponible
- Heures creuses internes VE actives
- État de la liaison (code + texte)
- État de la liaison (texte)
- État de la liaison (code)
- Courant de charge VE
- I charge manual
- Puissance de charge
- Recharge cumulée VE
- Temps de charge VE
- U_reseau
- PWM borne VE
- nb_depassement_hard
- nb_depassement_soft
- I_max
- I_min_c
- Version
- DateVersion
- CarteVersion
- Puissance S VE
- maxWhInput
- DateHoraireDefin
- P_seuil_regul
- fact_Icharge
- Production-Consommation VE


v0.1.5.1 : correction de la jauge pour éviter le point coloré résiduel à 0 A.


## Exemple Dashboard Mushroom


```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: select.routeur_ve_mode_de_fonctionnement
      - type: entity
        entity: binary_sensor.routeur_ve_regulation_auto_ve_disponible

  - type: custom:mushroom-number-card
    entity: number.routeur_ve_i_charge_manual
    name: Courant de charge

  - type: custom:mushroom-entity-card
    entity: sensor.routeur_ve_courant_de_charge_ve
    name: Courant réel

  - type: custom:mushroom-entity-card
    entity: sensor.routeur_ve_puissance_de_charge
    name: Puissance

  - type: custom:mushroom-entity-card
    entity: sensor.routeur_ve_recharge_cumulee_ve
    name: Energie

  - type: custom:mushroom-entity-card
    entity: sensor.routeur_ve_temps_de_charge_ve
    name: Temps
```
