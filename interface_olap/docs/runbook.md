# Runbook - Interface OLAP

Guide d'exploitation pour l'interface OLAP des tableaux de bord BI.

## 🚀 Démarrage

### Installation initiale

```powershell
cd interface_olap
copy .env.example .env
# Éditer .env avec vos identifiants PostgreSQL
npm install
```

### Lancement quotidien

```powershell
cd interface_olap
npm start
```

Ouvrir `http://localhost:3030`

## 📋 Prérequis

### Base de données
- PostgreSQL local démarré
- Base `erp_distribution_dwh` existante
- Tables DWH peuplées (exécuter `python ../BI/run_pipeline.py` au moins une fois)

### Configuration (.env)
```env
PORT=3030
DWH_PGHOST=localhost
DWH_PGPORT=5432
DWH_PGDATABASE=erp_distribution_dwh
DWH_PGUSER=postgres
DWH_PGPASSWORD=votre_mot_de_passe
```

## 🔧 Utilisation

### Navigation
- **Menu latéral** : Accès rapide aux 4 pages
- **SPA** : Navigation instantanée sans rechargement
- **Responsive** : Fonctionne sur desktop et tablette

### Pages

#### 1. Pipeline ETL (`#/`)
- **Bouton "Lancer le pipeline"** : Exécution normale (détection de changement)
- **Bouton "Forcer"** : Rechargement complet même si aucune donnée nouvelle
- **Terminal** : Logs en temps réel avec message d'information
- **Statut** : Prêt / En cours / Succès / Erreur

#### 2. Dashboard Stratégique (`#/strategic`)
- **KPIs globaux** : CA, profit, marge, commandes, clients, panier moyen
- **Évolution mensuelle** : Graphique linéaire CA sur 6 mois
- **Segments clients** : Répartition CA par segment (doughnut)
- **Top régions** : Barres horizontales CA par région
- **Top produits** : Barres horizontales CA par produit

#### 3. Dashboard Tactique (`#/tactical`)
- **Filtre période** : 30/60/90 jours ou tout
- **KPIs période** : CA total, commandes, moyenne/jour, marge globale
- **Tendance quotidienne** : Graphique area CA quotidien
- **Catégories** : Barres groupées CA + profit par catégorie
- **Statuts commandes** : Barres nombre par statut
- **Modes livraison** : Barres CA par mode

#### 4. Dashboard Opérationnel (`#/operational`)
- **Commandes récentes** : Tableau 20 dernières commandes avec statuts
- **Alertes stock** : Tableau produits avec quantité < 10 (coloré)
- **Transitions** : Barres nombre par type de transition
- **Régions** : Barres horizontales commandes par région (30j)

## 🐛 Dépannage

### Erreurs fréquentes

#### "Erreur de connexion PostgreSQL"
- **Cause** : Mauvais identifiants dans `.env`
- **Solution** : Vérifier `DWH_PG*` variables, redémarrer serveur

#### "Graphiques vides"
- **Cause** : DWH non peuplé
- **Solution** : Exécuter `python ../BI/run_pipeline.py`

#### "Port 3030 déjà utilisé"
- **Cause** : Autre processus sur le port
- **Solution** : `taskkill /F /IM node.exe` ou changer `PORT` dans `.env`

#### "Pipeline ne se lance pas"
- **Cause** : Script Python non trouvé ou backend ERP arrêté
- **Solution** : Vérifier console serveur pour logs détaillés

### Vérifications post-démarrage

1. **Serveur démarré** : Console affiche "Interface OLAP demarree"
2. **Page accessible** : `http://localhost:3030` charge sans erreur
3. **Dashboards** : Chaque page affiche des données (pas vide)
4. **Pipeline** : Bouton fonctionne et affiche les logs

## 📊 Performance

### Temps de chargement typiques
- **Page initiale** : < 1s
- **Dashboard stratégique** : 200-500ms
- **Dashboard tactique** : 300-800ms (selon filtre)
- **Dashboard opérationnel** : 200-400ms

### Optimisations
- Requêtes SQL optimisées avec index
- Pas de rechargement automatique (manuel)
- Connexions PostgreSQL en pool (max 10)

## 🔄 Maintenance

### Quotidienne
- Vérifier que les dashboards affichent des données à jour
- Consulter les logs du pipeline si exécuté

### Hebdomadaire
- Vérifier l'espace disque (logs peuvent s'accumuler)
- Redémarrer le serveur si nécessaire

### Mensuelle
- Mettre à jour les dépendances `npm update`
- Vérifier les performances des requêtes SQL

## 📞 Support

Pour toute question :
1. Consulter ce runbook
2. Vérifier les logs dans la console du serveur
3. Tester avec `python ../BI/run_pipeline.py` en CLI
