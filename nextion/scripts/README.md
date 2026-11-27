# Outils Nextion maintenus

Sur le fork `stephdust/Flow.io-Waveshare:dev`, **seul nxwright** est utilisé
pour reconstruire le Nextion `NX4832K035_011` (480 × 320), version `7.0.0`.
L'ancien chemin Nextion2Text + patchage binaire HMI a été supprimé.

## Commandes uniques (depuis la racine)

```bash
pio run -e nextion             # nxwright → HMI + TFT → binary/ + manifest.json
pio run -e nextion -t manifest # TFT existant → binary/ + manifest.json
```

La commande complète vérifie les sources `nextion/tests/NX4832K035_011/7.0.0/source/`,
reconstruit le HMI, le réextrait pour vérification, compile le TFT, puis
publie les deux fichiers sous `nextion/releases/7.0.0/`. Les deux commandes
actualisent `binary/manifest.json` sans compiler l'ESP32 ni le SPIFFS.

## Fichiers utiles

| Script | Rôle |
|---|---|
| `pio_nextion_targets.py` | Déclare les cibles PlatformIO `nextion` et `manifest` |
| `run_nextion.py` | Séquence nxwright unique, isolation Python et publication |
| `render_nx_home.py` | Images de fond, jauges pH/ORP et anneau de pompe |
| `refresh_nextion_manifest.py` | Export du TFT et manifeste via le mécanisme existant |
| `test_nextion_wake.py` | Test de non-régression sur le réveil / `xpic` |
| `test_nextion_animation.py` | Test de non-régression sur la rotation de la pompe |

La chaîne principale est testée par
[`nextion-nxwright-redesign.yml`](../../.github/workflows/nextion-nxwright-redesign.yml)
et l'export rapide par
[`nextion-platformio-fast.yml`](../../.github/workflows/nextion-platformio-fast.yml).

Les fichiers des écrans Nextion 5″ et 7″, le firmware ESP32, SPIFFS et
la branche de Christophe ne sont **pas concernés**. La version reste `7.0.0`
jusqu'au PR. La compilation automatique ne dispense pas de valider le TFT sur
l'écran réel.
