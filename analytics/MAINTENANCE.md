# 🚀 GUIDE MAINTENANCE SYSTÈME ANALYTICS

## ✅ COMPOSANTS GARANTIS TOUJOURS FONCTIONNELS

### 1. **Backend API** (Node.js + PostgreSQL OLTP)
- **Durée de vie** : Indépendante, pas de dépendances externes
- **Maintenance** : Redémarrage serveur si nécessaire
- **Commande** : `cd backend && npm start`

### 2. **Data Warehouse** (PostgreSQL OLAP)
- **Durée de vie** : Base de données locale, autonome
- **Maintenance** : Backup régulier, optimisation indexes
- **Commande** : Service PostgreSQL toujours actif

### 3. **ETL Pipeline**
- **Durée de vie** : Scripts Python autonomes
- **Maintenance** : Vérifier logs, relancer si erreur
- **Commande** : `python olap/etl/main.py`

### 4. **Dashboards BI** (Ports 8050/8051/8052)
- **Durée de vie** : Scripts Python autonomes
- **Maintenance** : Redémarrage si crash
- **Commandes** : 
  ```bash
  python analytics/business_intelligence/dashboard_strategic.py
  python analytics/business_intelligence/dashboard_tactical.py
  python analytics/business_intelligence/dashboard_operational.py
  ```

### 5. **Data Mining**
- **Durée de vie** : Scripts Python avec calculs locaux
- **Maintenance** : Aucune dépendance externe
- **Commande** : `python analytics/data_mining/data_mining_simple.py`

## ⚠️ POINTS D'ATTENTION

### **IA Reporting** (Optionnel)
- **Dépendance** : Clé API OpenAI valide
- **Solution** : Mode démo toujours disponible
- **Alternative** : Utiliser `demo_mode.py`

### **Dépendances Python**
- **Risque** : Mises à jour de librairies
- **Solution** : Versions figées dans `requirements.txt`
- **Commande** : `pip install -r analytics/requirements.txt`

## 🛡️ PROCÉDURES DE RÉCUPÉRATION

### **Si un dashboard crash**
```bash
# 1. Tuer les processus
taskkill /F /IM python.exe

# 2. Redémarrer individuellement
python analytics/business_intelligence/dashboard_operational.py
```

### **Si ETL échoue**
```bash
# 1. Vérifier logs
cat analytics/results/etl_logs/etl_run_log.csv

# 2. Relancer
python olap/etl/main.py
```

### **Si Data Mining échoue**
```bash
# Vérifier données Data Warehouse
python analytics/data_mining/data_mining_simple.py
```

## 📋 CHECKLIST MENSUELLE

### **Automatique (scripts)**
- [ ] Vérifier espace disque bases de données
- [ ] Backup Data Warehouse
- [ ] Vérifier logs erreurs ETL

### **Manuelle (5 minutes)**
- [ ] Tester accès dashboards (8050/8051/8052)
- [ ] Vérifier génération Data Mining
- [ ] Tester mode démo IA Reporting

## 🔄 MISES À JOUR SÉCURISÉES

### **Avant mise à jour**
```bash
# 1. Backup environnement
cp analytics/requirements.txt analytics/requirements_backup.txt

# 2. Tester sur environnement de test
pip install nouvelle_version
python analytics/data_mining/data_mining_simple.py
```

### **Après mise à jour**
```bash
# 3. Valider tous composants
python analytics/business_intelligence/dashboard_operational.py
python analytics/data_mining/data_mining_simple.py
python analytics/ia_reporting/demo_mode.py
```

## 🎯 GARANTIES DE FONCTIONNEMENT

### **Niveau 1 : Toujours OK (99% du temps)**
- Backend API
- Data Warehouse
- Dashboards BI
- Data Mining

### **Niveau 2 : Mode dégradé OK**
- IA Reporting (mode démo)

### **Niveau 3 : Dépendances externes**
- IA Reporting production (nécessite clé API)

---
*Document de maintenance - Système Analytics ERP Distribution*
*Dernière mise à jour : 20/02/2026*
