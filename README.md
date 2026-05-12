# SDF Logic Studio - Guide d'Utilisation

Ce projet est un outil de modélisation procédurale basé sur les **SDF (Signed Distance Functions)** directement intégré dans Blender. Il permet de créer des formes complexes en combinant des primitives mathématiques (sphères, boîtes, etc.) via des opérations booléennes en temps réel.

---

## Comment lancer le projet

Pour faire fonctionner l'outil, suivez précisément ces étapes :

1.  **Ouvrir Blender** : Lancez votre fichier `Projet_Geo_numérique.blend`.
2.  **Accéder à l'Éditeur de Texte** :
    * Repérez l'espace de travail dédié au code (onglet **Scripting** en haut de l'écran ou une fenêtre de type *Text Editor*).
3.  **Charger le script** :
    * Dans la liste des fichiers texte internes à Blender, cherchez et sélectionnez le fichier nommé `projet.py`.
4.  **Exécuter le programme** :
    * Cliquez sur le bouton **"Run Script"** (l'icône ▶️ Play) en haut à droite de l'éditeur de texte.
    * Le panneau **"SDF Tool"** apparaîtra alors dans la barre latérale droite (touche `N`) de la Vue 3D.

---

## Résumé du Projet

L'outil transforme des objets "vides" (Empties) en formes géométriques réelles. 
* Chaque objet nommé avec le préfixe `CTRL_` sert de guide.
* Le script calcule mathématiquement la distance de chaque point de l'espace par rapport à ces guides.
* L'algorithme **Marching Cubes** génère ensuite un maillage (Mesh) visible autour de ces équations.
* L'avantage principal est la possibilité de faire des **Unions Lissées** (Smooth Union), permettant de fusionner deux objets comme s'ils étaient faits de pâte à modeler ou de liquide (effet "Metaballs").

---

## Manipulations et Raccourcis

### Dans la Vue 3D
* **Sélection simple** : `Clic Gauche` sur un contrôleur (le cube filaire).
* **Sélection multiple** (Indispensable pour les opérations) : Maintenez `Maj` (Shift) et faites `Clic Gauche` sur plusieurs contrôleurs. 
    * *Note : Le dernier objet sélectionné devient la **Base** (contour jaune clair).*
* **Déplacement / Rotation / Échelle** : Utilisez les touches classiques de Blender (`G`, `R`, `S`). Le maillage se mettra à jour automatiquement dès que vous relâchez l'objet.

### Dans le Panneau "SDF Tool" (Barre N)
* **Ajouter** : Crée une nouvelle forme primitive à l'origine.
* **Mode Lissage** : Cochez cette case pour transformer les unions nettes en fusions organiques.
* **Union / Soustraction** : Apparaissent uniquement si **2 objets** ou plus sont sélectionnés.
* **Résolution** : Augmentez la valeur pour un maillage plus précis (attention : ralentit le calcul).
* **Lissage Mesh** : Ajuste la fluidité du maillage final pour enlever l'aspect "escalier" des cubes.

### Utilisation de la Molette (Astuces Avancées)
La molette est cruciale pour la précision lors d'un agrandissement ou d'un déplacement :

1.  **Contrôle des Axes** : Après avoir appuyé sur **S** (Scale) ou **G** (Move), cliquez sur la **Molette (bouton central)** et déplacez légèrement la souris vers un axe : Blender "aimantera" l'objet sur l'axe X (rouge), Y (vert) ou Z (bleu).
2.  **Changement d'Axe Rapide** : En restant en mode transformation, faire défiler la molette permet parfois (selon vos réglages Blender) de basculer entre les axes globaux et locaux.
3.  **Précision** : Maintenez **Maj (Shift)** tout en déplaçant la souris (ou en utilisant la molette pour certains réglages) pour effectuer des changements très lents et précis.

### Sélection
* **Clic Gauche** : Sélectionner un contrôleur.
* **Maj + Clic Gauche** : Sélectionner plusieurs objets (Le dernier est la **Base**, en jaune).
* **Alt + Clic Gauche** : Si plusieurs objets se chevauchent, ouvre une liste pour choisir lequel sélectionner.

---

## Conseil de performance
La molette de la souris sert aussi au **Zoom** dans la vue 3D. Si votre scène devient lourde à cause d'une **Résolution** trop haute (ex: 128), le zoom peut saccader. Baissez la résolution pendant les phases de déplacement et remontez-la pour le rendu final.

---

## Notes importantes
* Ne supprimez pas le préfixe `CTRL_` des objets, sinon le script ne les reconnaîtra plus.
* Si le maillage disparaît, vérifiez que vos objets sont bien à l'intérieur de la zone définie par le paramètre **"Bounds"**.
