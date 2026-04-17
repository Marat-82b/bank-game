import json
import os
from datetime import datetime, timezone
import math

# Путь к папке с кошельками
WALLETS_DIR = 'wallets'
ASSETS_DIR = 'assets'

def load_asset_config(asset_file):
    """Загружает параметры актива (процентная ставка)"""
    with open(os.path.join(ASSETS_DIR, asset_file), 'r', encoding='utf-8') as f:
        return json.load(f)

def accrue_interest_for_wallet(wallet_path, assets_config):
    """Начисляет проценты на все активы в кошельке кроме CASH"""
    with open(wallet_path, 'r+', encoding='utf-8') as f:
        data = json.load(f)
        
        # Получаем время последнего начисления
        last_calc_str = data.get('last_interest_calc')
        if not last_calc_str:
            # Если нет записи, ставим текущее время и выходим
            data['last_interest_calc'] = datetime.now(timezone.utc).isoformat()
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
            return False
        
        last_calc = datetime.fromisoformat(last_calc_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta_seconds = (now - last_calc).total_seconds()
        
        if delta_seconds <= 0:
            return False  # Время не пришло или сбой
            
        updated = False
        balances = data.get('balances', {})
        
        for asset, amount in balances.items():
            if asset == 'CASH':
                continue  # На кэш проценты не капают (инфляция только через эмиссию)
            
            # Ищем конфиг актива
            asset_config = assets_config.get(asset)
            if not asset_config:
                continue
                
            apy = asset_config.get('interest_rate_apy', 0.0)
            if apy <= 0:
                continue
                
            # Формула непрерывного начисления процентов
            # A = P * (1 + r)^(t_seconds / seconds_in_year)
            seconds_in_year = 365.25 * 24 * 3600
            new_amount = amount * ((1 + apy) ** (delta_seconds / seconds_in_year))
            
            balances[asset] = round(new_amount, 8)
            updated = True
            
        if updated:
            data['balances'] = balances
            data['last_interest_calc'] = now.isoformat()
            # Увеличиваем nonce (защита от коллизий при коммитах)
            data['nonce'] = data.get('nonce', 0) + 1
            
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()
        return updated

def main():
    # Загружаем конфигурации всех активов
    assets_config = {}
    if os.path.exists(ASSETS_DIR):
        for filename in os.listdir(ASSETS_DIR):
            if filename.endswith('.json'):
                asset_data = load_asset_config(filename)
                ticker = asset_data.get('ticker')
                if ticker:
                    assets_config[ticker] = asset_data
    
    # Создаем папку wallets если её нет
    os.makedirs(WALLETS_DIR, exist_ok=True)
    
    # Обрабатываем все JSON файлы в wallets
    any_change = False
    for filename in os.listdir(WALLETS_DIR):
        if filename.endswith('.json'):
            wallet_path = os.path.join(WALLETS_DIR, filename)
            changed = accrue_interest_for_wallet(wallet_path, assets_config)
            if changed:
                any_change = True
                print(f"✅ Проценты начислены для {filename}")
    
    if not any_change:
        print("ℹ️ Нет кошельков для начисления процентов.")

if __name__ == "__main__":
    main()
