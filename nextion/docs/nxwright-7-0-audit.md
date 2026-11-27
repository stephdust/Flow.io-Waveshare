# Évaluation de nxwright — Nextion NX4832K035_011 / 7.0.0

Ce test est **diagnostique et non destructif** : il ne modifie aucun fichier HMI/TFT
du dépôt, ne compile pas de TFT, n'installe rien sur un écran et ne change pas
`platformio.ini`. Les Nextion 5″ et 7″ sont entièrement hors périmètre.

## Références

- Projet tiers : https://github.com/nixiewright/nxwright
- Commit nxwright épinglé : `e9443a409cc9deb866db7486854fa962d382accc`.
- Workflow : [nextion-nxwright-audit.yml](../../.github/workflows/nextion-nxwright-audit.yml).
- Script : [audit_3p5_nxwright.py](../scripts/audit_3p5_nxwright.py).
- Source fonctionnelle de référence : `backup/nextion-v7-validated-20261127`,
  objet Git `ac941badd17a3f0b8d27da4a29cc5135d5a0986c`.
- Source en cours de développement :
  `nextion/releases/7.0.0/FlowIO_Nextion_NX4832K035_011-7.0.0.HMI` sur `dev`.

## Opérations dans GitHub Actions

Le workflow installe nxwright sur un runner Python 3.11 temporaire et exécute
indépendamment sur chaque HMI :

1. `nxwright extract --list-unknown` pour détecter les blocs non pris en charge ;
2. `nxwright extract` pour obtenir le projet en sources textuelles ;
3. `nxwright check` pour vérifier la validité des pages, scripts et images ;
4. `nxwright build --no-lock` vers un HMI temporaire, hors du dépôt ;
5. `nxwright diff` puis `nxwright report` pour identifier les différences.

Les résultats complets sont dans le résumé GitHub Actions et dans l'artefact
`Nextion-NX4832K035-7.0.0-NXWRIGHT-AUDIT` (14 jours).
L'échec d'une extraction, d'un contrôle ou de la reconstruction rend le test rouge.

## Conditions de passage à une intégration de production

Une validation supplémentaire dans Nextion Editor et sur le vrai
`NX4832K035_011` est obligatoire. Confirmer le rendu des jauges pH/ORP,
le retour après veille, la bonne orientation des images, les événements tactiles
et les objets du protocole série avant de permettre à nxwright de compiler
un TFT Flow.io. Les HMI reconstruits lors de cet audit ne sont **jamais**
utilisés pour le déploiement.

## Chaîne de compilation nxwright via PlatformIO (27 novembre 2026)

Le [workflow de compilation NX4832K035](../../.github/workflows/nextion-nxwright-redesign.yml)
utilise désormais **la même commande que sur le poste local** :

```bash
pio run -e nextion
```

La source modifiable est `nextion/tests/NX4832K035_011/7.0.0/source/`.
Cette commande effectue : `nxwright check`, reconstruction HMI, réextraction,
`nxwright compile --download`, vérification TFT, copie du HMI/TFT dans
`nextion/releases/7.0.0/`, et régénération de `binary/manifest.json`.

Pour mettre à jour uniquement l'export TFT et le manifeste sans compiler :

```bash
pio run -e nextion -t manifest
```

[L'exécution CI complète a réussi](https://github.com/stephdust/Flow.io-Waveshare/actions/runs/46010307421).
Le développement reste sur `stephdust/dev`, sans PR vers `christophebelmont/dev`
avant la validation physique. Les Nextion 5″/7″ restent strictement inchangés.
Le manifeste généré localement doit être publié avec le TFT sur le serveur HTTP.
