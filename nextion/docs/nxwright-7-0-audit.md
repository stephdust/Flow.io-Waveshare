# Évaluation de nxwright — Nextion NX4832K035_011 / 7.0.0

Ce test est **diagnostique et non destructif** : il ne modifie aucun fichier HMI/TFT
du dépôt, ne compile pas de TFT, n'installe rien sur un écran et ne change pas
`platformio.ini`. Les Nextion 5″ et 7″ sont entièrement hors périmètre.

## Références

- Projet tiers : https://github.com/nixiewright/nxwright
- Commit nxwright épinglé : `e9443a409cc9deb866db7486854fa962d382accc`.
- Workflow : [nextion-nxwright-audit.yml](../../.github/workflows/nextion-nxwright-audit.yml).
- Script : [audit_3p5_nxwright.py](../tools/audit_3p5_nxwright.py).
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
