import csv
import random
import uuid
from datetime import datetime, timedelta
import faker

# Use Swedish locale for names and addresses
fake = faker.Faker('sv_SE')

# Configuration
NUM_USERS = 100
NUM_TRANSACTIONS = 1000
START_DATE = datetime.now() - timedelta(days=90)

# Occupations and Risk Profiles (Swedish)
OCCUPATIONS = {
    'Student': {'base_risk': 0.1, 'income_range': (0, 200000), 'pep_eligible': False},
    'Lärare': {'base_risk': 0.2, 'income_range': (400000, 700000), 'pep_eligible': False},
    'Sjuksköterska': {'base_risk': 0.2, 'income_range': (600000, 900000), 'pep_eligible': False},
    'Mjukvaruutvecklare': {'base_risk': 0.3, 'income_range': (800000, 1500000), 'pep_eligible': False},
    'Importör': {'base_risk': 0.6, 'income_range': (500000, 2000000), 'pep_eligible': False},
    'Arbetslös': {'base_risk': 0.4, 'income_range': (0, 100000), 'pep_eligible': False},
    'Företagare': {'base_risk': 0.5, 'income_range': (1000000, 5000000), 'pep_eligible': False},
    # PEP-eligible occupations
    'Politiker': {'base_risk': 0.7, 'income_range': (600000, 1200000), 'pep_eligible': True},
    'Diplomat': {'base_risk': 0.6, 'income_range': (700000, 1400000), 'pep_eligible': True},
    'Domare': {'base_risk': 0.5, 'income_range': (800000, 1500000), 'pep_eligible': True},
    'Högre tjänsteman': {'base_risk': 0.6, 'income_range': (900000, 1800000), 'pep_eligible': True},
}

users = []
transactions = []
alerts = []

def generate_users():
    print("Generating Users...")
    pep_count = 0
    target_peps = 5  # Only 5 PEPs out of 100 users
    
    for _ in range(NUM_USERS):
        occupation = random.choice(list(OCCUPATIONS.keys()))
        profile = OCCUPATIONS[occupation]
        
        # Determine PEP status
        is_pep = False
        if profile['pep_eligible'] and pep_count < target_peps:
            # 80% chance of being PEP if occupation is eligible
            if random.random() < 0.8:
                is_pep = True
                pep_count += 1
        
        user = {
            'user_id': f"U-{uuid.uuid4().hex[:8].upper()}",
            'name': fake.name(),
            'occupation': occupation,
            'email': fake.email(),
            'phone': fake.phone_number(),
            'address': fake.address().replace('\n', ', '),
            'annual_income': random.randint(*profile['income_range']),
            'risk_score': min(1.0, max(0.0, random.gauss(profile['base_risk'], 0.1))),
            'joined_date': (START_DATE - timedelta(days=random.randint(0, 1000))).strftime('%Y-%m-%d'),
            'is_pep': is_pep
        }
        users.append(user)

def generate_transactions():
    print("Generating Background Transactions...")
    for _ in range(NUM_TRANSACTIONS):
        sender = random.choice(users)
        receiver = random.choice(users)
        while receiver['user_id'] == sender['user_id']:
            receiver = random.choice(users)
            
        # SEK amounts: 100-50,000 SEK (roughly 10-5000 USD equivalent)
        amount = round(random.uniform(100, 50000), 2)
        txn_date = START_DATE + timedelta(days=random.randint(0, 90))
        
        txn = {
            'txn_id': f"TX-{uuid.uuid4().hex[:12].upper()}",
            'sender_id': sender['user_id'],
            'receiver_id': receiver['user_id'],
            'amount': amount,
            'currency': 'SEK',
            'timestamp': txn_date.isoformat(),
            'txn_type': 'TRANSFER'
        }
        transactions.append(txn)

def inject_smurfing_pattern():
    print("Injecting Smurfing Pattern...")
    # A 'smurf' receives many small deposits and sends one large one
    smurf = random.choice(users)
    beneficiary = random.choice(users)
    while beneficiary['user_id'] == smurf['user_id']:
        beneficiary = random.choice(users)
        
    print(f"  -> Smurf: {smurf['name']} ({smurf['user_id']})")
    print(f"  -> Beneficiary: {beneficiary['name']} ({beneficiary['user_id']})")
    
    # 10 small deposits into smurf account
    total_amount = 0
    for _ in range(10):
        # Just under 100k SEK reporting limit (roughly 10k USD equivalent)
        amount = round(random.uniform(80000, 95000), 2)
        total_amount += amount
        txn_date = START_DATE + timedelta(days=random.randint(60, 70))
        
        txn = {
            'txn_id': f"TX-SMURF-IN-{uuid.uuid4().hex[:8].upper()}",
            'sender_id': 'EXTERNAL_DEPOSIT', # Simulating cash deposit
            'receiver_id': smurf['user_id'],
            'amount': amount,
            'currency': 'SEK',
            'timestamp': txn_date.isoformat(),
            'txn_type': 'DEPOSIT'
        }
        transactions.append(txn)
        
    # 1 large transfer out
    txn_out = {
        'txn_id': f"TX-SMURF-OUT-{uuid.uuid4().hex[:8].upper()}",
        'sender_id': smurf['user_id'],
        'receiver_id': beneficiary['user_id'],
        'amount': total_amount,
        'currency': 'SEK',
        'timestamp': (START_DATE + timedelta(days=71)).isoformat(),
        'txn_type': 'TRANSFER'
    }
    transactions.append(txn_out)
    
    # Create Alert
    alert = {
        'alert_id': str(uuid.uuid4()),
        'user_id': smurf['user_id'],
        'trigger_reason': 'Strukturering: Flera insättningar strax under rapporteringsgräns',
        'status': 'NY',
        'created_at': (START_DATE + timedelta(days=72)).isoformat(),
        'severity': 'HÖG'
    }
    alerts.append(alert)

def inject_mule_ring_pattern():
    print("Injecting Mule Ring Pattern...")
    # Multiple mules sending to one controller
    controller = random.choice(users)
    mules = random.sample([u for u in users if u['user_id'] != controller['user_id']], 5)
    
    print(f"  -> Controller: {controller['name']} ({controller['user_id']})")
    
    for mule in mules:
        # Mule receives funds from external source (150k-250k SEK)
        amount = round(random.uniform(150000, 250000), 2)
        txn_date = START_DATE + timedelta(days=random.randint(80, 82))
        
        transactions.append({
            'txn_id': f"TX-MULE-IN-{uuid.uuid4().hex[:8].upper()}",
            'sender_id': 'EXTERNAL_WIRE',
            'receiver_id': mule['user_id'],
            'amount': amount,
            'currency': 'SEK',
            'timestamp': txn_date.isoformat(),
            'txn_type': 'WIRE_IN'
        })
        
        # Mule forwards to controller
        transactions.append({
            'txn_id': f"TX-MULE-OUT-{uuid.uuid4().hex[:8].upper()}",
            'sender_id': mule['user_id'],
            'receiver_id': controller['user_id'],
            'amount': amount * 0.95, # Keeps cut
            'currency': 'SEK',
            'timestamp': (datetime.fromisoformat(txn_date.isoformat()) + timedelta(hours=2)).isoformat(),
            'txn_type': 'TRANSFER'
        })
        
        # Alert on Mule
        alerts.append({
            'alert_id': str(uuid.uuid4()),
            'user_id': mule['user_id'],
            'trigger_reason': 'Snabb rörelse: Pengar överförda omedelbart efter mottagande',
            'status': 'NY',
            'created_at': (datetime.fromisoformat(txn_date.isoformat()) + timedelta(days=1)).isoformat(),
            'severity': 'MEDEL'
        })

def inject_false_positives():
    print("Injecting False Positives...")
    # Scenario 1: High Net Worth Individual making a large but affordable purchase
    # Find a rich user
    rich_users = [u for u in users if u['annual_income'] > 1500000]
    if rich_users:
        rich_user = random.choice(rich_users)
        print(f"  -> False Positive (Affordability): {rich_user['name']} (Income: ${rich_user['annual_income']})")
        
        # Transaction: Large but < 20% of income
        amount = round(rich_user['annual_income'] * 0.15, 2)
        txn_date = START_DATE + timedelta(days=random.randint(50, 60))
        
        transactions.append({
            'txn_id': f"TX-FP-RICH-{uuid.uuid4().hex[:8].upper()}",
            'sender_id': rich_user['user_id'],
            'receiver_id': 'EXTERNAL_MERCHANT_LUXURY_GOODS',
            'amount': amount,
            'currency': 'SEK',
            'timestamp': txn_date.isoformat(),
            'txn_type': 'PURCHASE'
        })
        
        alerts.append({
            'alert_id': str(uuid.uuid4()),
            'user_id': rich_user['user_id'],
            'trigger_reason': 'Högt värde transaktion: Enskild transaktion > 100 000 kr',
            'status': 'NY',
            'created_at': (datetime.fromisoformat(txn_date.isoformat()) + timedelta(days=1)).isoformat(),
            'severity': 'MEDEL'
        })

    # Scenario 2: High Geo Risk but Occupation explains it (Importer)
    importers = [u for u in users if u['occupation'] == 'Importör']
    if importers:
        importer = random.choice(importers)
        print(f"  -> False Positive (Context): {importer['name']} (Importer)")
        
        # Transaction with high risk country (200k-500k SEK)
        amount = round(random.uniform(200000, 500000), 2)
        txn_date = START_DATE + timedelta(days=random.randint(40, 50))
        
        transactions.append({
            'txn_id': f"TX-FP-GEO-{uuid.uuid4().hex[:8].upper()}",
            'sender_id': importer['user_id'],
            'receiver_id': 'EXTERNAL_SUPPLIER_HIGH_RISK_GEO',
            'amount': amount,
            'currency': 'SEK',
            'timestamp': txn_date.isoformat(),
            'txn_type': 'WIRE_OUT'
        })
        
        alerts.append({
            'alert_id': str(uuid.uuid4()),
            'user_id': importer['user_id'],
            'trigger_reason': 'Geografisk risk: Stor överföring till högriskjurisdiktion',
            'status': 'NY',
            'created_at': (datetime.fromisoformat(txn_date.isoformat()) + timedelta(days=1)).isoformat(),
            'severity': 'HÖG'
        })

def save_to_csv():
    print("Saving to CSV...")
    with open('users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=users[0].keys())
        writer.writeheader()
        writer.writerows(users)
        
    with open('transactions.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
        writer.writeheader()
        writer.writerows(transactions)
        
    with open('alerts.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=alerts[0].keys())
        writer.writeheader()
        writer.writerows(alerts)

if __name__ == "__main__":
    generate_users()
    generate_transactions()
    inject_smurfing_pattern()
    inject_mule_ring_pattern()
    inject_false_positives()
    save_to_csv()
    print("Done! Generated users.csv, transactions.csv, alerts.csv")
