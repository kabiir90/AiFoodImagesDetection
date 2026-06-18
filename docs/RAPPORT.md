# Projet Machine Learning — Détection et estimation calorique des aliments

**Application : santé & nutrition — « Food Scanner »**
Étudiant : **Mohamed Oulkabir** · Module : Machine Learning · Encadrant : Pr. M. Hain · Juin 2026

> Conversion en PDF : ouvrir ce fichier dans VS Code → « Markdown PDF », ou coller dans
> Word/Google Docs. Insérer les captures d'écran aux emplacements indiqués `[CAPTURE …]`.

---

## 1. Problème à résoudre

Le suivi nutritionnel manuel (saisie des aliments et des calories) est fastidieux et source
d'erreurs, ce qui décourage les utilisateurs souhaitant contrôler leur alimentation
(perte de poids, sport, diabète, etc.).

**Objectif :** à partir d'une simple **photo d'un plat**, reconnaître automatiquement
l'aliment, puis estimer ses **calories** et ses **macronutriments** (protéines, lipides,
glucides), et les enregistrer dans un journal alimentaire avec suivi des objectifs quotidiens.

**Chaîne de traitement :**
`Caméra / Photo → Détection de l'aliment (modèle IA) → Classification (1 parmi 101 plats) → Estimation calories & macros → Journalisation & visualisation`

---

## 2. Type d'apprentissage utilisé et justification

**Apprentissage supervisé.**

- Le jeu de données **Food-101** fournit pour chaque image une **étiquette** (la catégorie
  du plat). Le modèle apprend donc une fonction `image → classe` à partir d'exemples
  **étiquetés** : c'est la définition de l'apprentissage supervisé.
- Il ne s'agit pas d'apprentissage **non supervisé** (aucune recherche de structure cachée /
  clustering : les classes sont connues à l'avance), ni d'apprentissage **par renforcement**
  (pas d'agent ni de récompense ; le système ne prend pas de décisions séquentielles dans un
  environnement).
- Plus précisément, c'est un problème de **classification supervisée multi-classes**
  (101 classes mutuellement exclusives) à partir d'images.

---

## 3. Modèle retenu et justification

**Modèle : réseau de neurones convolutif (CNN) MobileNetV2 + apprentissage par transfert
(transfer learning).**

On réutilise **MobileNetV2** pré-entraîné sur **ImageNet** (≈ 1,4 M d'images) comme extracteur
de caractéristiques, auquel on ajoute une tête de classification adaptée à nos 101 classes :

```
Entrée (224×224×3) → MobileNetV2 (gelé puis fine-tuné) → GlobalAveragePooling2D
→ Dropout(0.2) → Dense(101, softmax)
```

**Raisons du choix :**
1. **Transfer learning** : Food-101 (101 000 images) est insuffisant pour entraîner un CNN
   depuis zéro ; réutiliser des poids ImageNet donne une bonne précision avec peu d'epochs.
2. **MobileNetV2** est **léger** (~3,5 M paramètres) : il s'exécute **dans le navigateur**
   via TensorFlow.js, ce qui permet un déploiement **hors-ligne** sur le poste Node-RED, sans
   serveur GPU.
3. **Stratégie en deux phases** : (a) on entraîne d'abord la tête (base gelée), puis (b) on
   **fine-tune** les dernières couches de la base à faible taux d'apprentissage (1e-5) pour
   spécialiser le modèle sur les aliments.
4. Fonction de perte **entropie croisée catégorielle** (sparse categorical cross-entropy),
   optimiseur **Adam**, métrique **accuracy** (+ top-5).

---

## 4. Données exploitées

### 4.1 Source
**Food-101** (École Polytechnique Fédérale de Zurich, dataset public de référence,
disponible aussi sur Kaggle). Téléchargé localement dans `food-101/`.

### 4.2 Variables principales
- **Variable d'entrée (X)** : image RGB d'un plat (taille variable, redimensionnée à 224×224).
- **Variable cible (y)** : la **catégorie** du plat, parmi **101 classes**
  (ex. `pizza`, `sushi`, `hamburger`, `caesar_salad`…).
- **Données dérivées** (table nutritionnelle `calories.json`) : pour chaque classe, les
  **calories**, la **portion** type, et les **macros** (protéines / lipides / glucides).

### 4.3 Volume du jeu de données
| Élément | Valeur |
|---|---|
| Nombre de classes | **101** |
| Images par classe | **1 000** |
| **Total images** | **101 000** |
| Découpage officiel | **75 750** entraînement / **25 250** test |
| Taille sur disque | ~5 Go (images JPEG) |

### 4.4 Préparation et prétraitement
Réalisés dans le pipeline `tf.data` (script `training/train.py`) :
1. **Lecture** du découpage officiel (`meta/train.txt`, `meta/test.txt`).
2. **Décodage JPEG** et **redimensionnement** à **224×224** (taille d'entrée de MobileNetV2).
3. **Normalisation** des pixels vers l'intervalle **[-1, 1]** (`pixel/127.5 - 1`), identique
   côté navigateur pour garantir la cohérence entraînement/inférence.
4. **Augmentation de données** (uniquement à l'entraînement) : **flip horizontal** aléatoire
   et **variation de luminosité**, pour améliorer la généralisation et réduire le surapprentissage.
5. **Mélange** (shuffle), **mise en lots** (batch = 32) et **préchargement** (prefetch) pour
   accélérer l'entraînement.
6. **Encodage des étiquettes** en indices entiers (0–100).

> Remarque : Food-101 est un jeu de **classification** (un plat centré par image, sans boîtes
> englobantes). La détection multi-aliments par boîtes (YOLO) constitue une évolution future.

---

## 5. Résultats et indicateurs de performance

**Protocole d'évaluation :** entraînement sur les 75 750 images, évaluation sur les 25 250
images de **test** jamais vues. Indicateurs : **exactitude top-1**, **exactitude top-5**,
**perte (loss)**, suivi des **courbes d'apprentissage** (accuracy/loss par epoch).

### 5.1 Résultats obtenus

Évaluation sur les **25 250 images de test** (jamais vues à l'entraînement) :

| Indicateur | Valeur |
|---|---|
| Exactitude **Top-1** (test) | **50,7 %** |
| Exactitude **Top-5** (test) | **78,9 %** |
| Perte (test) | **2,20** |
| Nombre de paramètres | **≈ 2,39 millions** |
| Nombre de classes | 101 |

> Valeurs produites automatiquement (`training/eval.py` → `artifacts/metrics.json`).
> Le modèle de référence aléatoire obtiendrait ≈ 1 % (1/101) ; notre modèle atteint donc
> **~51 fois** mieux que le hasard au Top-1.

### 5.2 Interprétation des indicateurs
- **Top-1 = 50,7 %** : le bon plat est proposé en 1ᵉʳ choix dans la moitié des cas — très
  honorable pour **101 classes** souvent visuellement proches.
- **Top-5 = 78,9 %** : la bonne classe figure parmi les 5 plus probables près de 4 fois sur 5.
  C'est l'indicateur le plus pertinent ici, car des plats se ressemblent fortement
  (*bread pudding* vs *carrot cake*, *steak* vs *filet mignon*) ; l'interface affiche
  d'ailleurs les **« autres correspondances possibles »**.
- L'application affiche un **score de confiance** par prédiction avec un code couleur
  (faible / moyen / élevé) pour signaler les détections incertaines.

**Limite & marge de progression (honnête) :** l'entraînement a été réalisé **sur CPU** et la
phase de *fine-tuning* n'a été que **partiellement** menée (interruption liée à la veille de la
machine). La littérature montre que MobileNetV2 entièrement *fine-tuné* sur Food-101 atteint
**~75–82 % Top-1** : poursuivre le *fine-tuning* (GPU, plus d'epochs) est la principale piste
d'amélioration, sans changer l'architecture ni le pipeline.

`[CAPTURE 1 : courbe d'apprentissage / sortie de metrics.json]`

---

## 6. Partie bonus — Workflow Node-RED

Le déploiement utilise **Node-RED** : le modèle TensorFlow.js s'exécute dans le tableau de
bord (navigateur), et un **flow** orchestre l'intégralité de la chaîne.

`[CAPTURE 2 : le workflow Node-RED — les 3 groupes : Intake / Routing / Analytics]`
`[CAPTURE 3 : le tableau de bord /ui avec une prédiction et les macros]`

### 6.1 Les 4 étapes de la solution dans le flow

| Étape | Nœud(s) Node-RED | Rôle |
|---|---|---|
| **1. Acquisition** | `ui_template` *(Food Scanner)* | Capture via **caméra** ou **upload** d'une photo. |
| **2. Prétraitement** | code TensorFlow.js + nœud **`function` « Normalize & validate »** | Redimensionnement 224×224, normalisation [-1,1] ; validation et mise en forme du résultat (libellé, confiance %, horodatage). |
| **3. Exécution du modèle** | `tf.loadLayersModel` (in-browser) | Inférence MobileNetV2 → probabilités sur 101 classes → meilleure classe + alternatives. |
| **4. Visualisation / sortie** | `ui_template` (cartes, KPIs, graphiques) + **`switch`**, **`rbe`**, **`function` « Daily totals »**, **`json`**, **`file`** | Affichage des résultats (calories, macros, score) ; routage selon la confiance ; filtrage des doublons ; cumul des totaux journaliers ; journalisation dans `food_scans.log`. |

### 6.2 Rôle des principaux nœuds

- **`ui_template` (Food Scanner)** — interface complète (HTML/CSS/JS) : scan, inférence
  TF.js, affichage des KPIs, graphiques et journal des repas. Émet chaque résultat (`msg.payload`).
- **`function` « Normalize & validate »** — nettoie/valide la prédiction, calcule la confiance
  en %, ajoute un horodatage ISO, rejette les messages vides.
- **`switch` « Confidence ≥ 60 % ? »** — **routage** : haute confiance → analytique & stockage ;
  faible confiance → marquage `needs_review`.
- **`rbe` (filter) « Skip repeat foods »** — **filtre** les scans identiques consécutifs pour
  éviter le bruit dans le journal.
- **`function` « Daily totals »** — maintient en **contexte de flux** le cumul journalier
  (calories + nombre de scans), réinitialisé chaque jour.
- **`json` + `file`** — sérialisation et **journalisation** des scans (`food_scans.log`, JSONL).
- **`catch` + `function` « format error »** — **gestion des erreurs** : capture toute erreur
  d'exécution du flow et l'affiche proprement (robustesse).

### 6.3 Exemple de résultat produit
> Photo d'une part de gâteau → **Détection : « Carrot cake »**, **415 kcal** / 1 part (110 g),
> **Protéines 8 g · Lipides 18 g · Glucides 56 g**, **confiance 82 % (élevée)**.
> Le repas est ajouté au **journal**, les **anneaux d'objectifs** (calories / protéines /
> lipides / glucides) et le **graphique des 7 derniers jours** se mettent à jour.

`[CAPTURE 4 : la carte « Detected food » avec calories, macros et alternatives]`

---

## 7. Conclusion

Le projet met en œuvre une **chaîne complète de Machine Learning supervisé** appliquée à la
santé : de la donnée (Food-101) au déploiement (Node-RED + TensorFlow.js). Le modèle
**MobileNetV2** par **transfer learning** offre un bon compromis **précision / légèreté**,
permettant une exécution **hors-ligne dans le navigateur**. L'application apporte une valeur
concrète : reconnaissance d'aliments, estimation calorique et nutritionnelle, et suivi
personnalisé des objectifs (IMC, besoins caloriques). **Pistes d'amélioration :** table
nutritionnelle vérifiée (USDA), estimation de la **portion** (Nutrition5k) et **détection
multi-aliments** (YOLO).

---

### Ressources fournies
- `training/train.py` — entraînement (transfer learning, 2 phases) ; `convert_to_tfjs.py` — export TF.js.
- `food-101/` — jeu de données ; `data/calories.json` — table nutritionnelle (101 classes).
- `node-red/flow.json` — workflow Node-RED ; `node-red/ui_template.html` — interface du tableau de bord.
- `training/artifacts/metrics.json` & `history.json` — indicateurs de performance.
