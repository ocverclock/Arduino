# MK2 PV Router v0.4.2 — calibration manuelle et Optiboot

## Fichiers

- `MK2_PV_Router_v0.4.2_CAL_MANUEL_SOURCE.zip` : sources de l'ATmega328P, projet PlatformIO, fichier Optiboot officiel et documentation.
- `fusion_mk2_v0.4.2_power_optiboot.py` : construit et vérifie un unique HEX contenant le firmware POWER et Optiboot, sans programmer la puce.

## Programmation ISP via Arduino Nano

1. Décompresser l'archive et ouvrir le dossier `FIRMWARE_MK2_REV2_1A/Mk2_fasterControl_Full` dans VS Code / PlatformIO.
2. Compiler **autonomous_power** (pas **autonomous_review**).
3. Télécharger le script `fusion_mk2_v0.4.2_power_optiboot.py` dans ce même dossier.
4. Depuis le terminal ouvert dans ce dossier : `python3 fusion_mk2_v0.4.2_power_optiboot.py`.
5. Vérifier le message `SUCCESS` puis, uniquement sur banc isolé du secteur, programmer l'ATmega : `avrdude -c stk500v1 -P /dev/ttyUSB0 -b 19200 -p m328p -U flash:w:MK2_v0.4.2_POWER_OPTIBOOT.hex:i`.
6. Vérifier les 32768 octets et les fusibles `E:FD H:DE L:FF`; répéter sur la seconde puce.

**Attention :** une gravure ISP de la Flash déclenche normalement un effacement global, y compris l'EEPROM tant que le fuse EESAVE n'est pas programmé. Les calibrations précédentes seront donc réinitialisées. La variante POWER autorise la commande du triac, mais sa polarité, l'isolation secteur et ses protections restent à valider sur le montage réel.

Pour les futures mises à jour **via Optiboot depuis l'ESP**, envoyer seulement `.pio/build/autonomous_power/firmware.hex`, et **jamais** le fichier fusionné.

Les profils ESPHome se trouvent dans le dépôt [esphome-config](https://github.com/ocverclock/esphome-config) : `ballon-routeur-esp32c6-v1.8.1-dev.yaml` et `ballon-routeur-esp32c6-v1.8.1-utilisation.yaml`.
