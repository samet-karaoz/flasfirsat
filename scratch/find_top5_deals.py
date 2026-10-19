import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from deal_hunter import hunt_best_deals, calculate_deal_viral_score, get_deal_discount_pct, get_deal_savings_tl
from product_verifier import verify_amazon_product

print("🔍 Canlı fırsatlar taranıyor (platform='all', limit=20)...")
candidates = hunt_best_deals(
    limit=20,
    platform="all",
    category="all",
    min_discount=20
)

print(f"\n📊 Toplam {len(candidates)} aday bulundu. Şimdi filtrelenip doğrulanıyor...\n")

results = []
for idx, d in enumerate(candidates, 1):
    title = d.get("title", "")
    url = d.get("store_url") or d.get("url") or ""
    old_p = d.get("old_price", "")
    new_p = d.get("new_price", "")
    pct = get_deal_discount_pct(d)
    savings = get_deal_savings_tl(d)
    score = calculate_deal_viral_score(d)
    
    print(f"[{idx}/{len(candidates)}] {title[:45]} | {old_p} -> {new_p} (-%{pct}) | Skor: {score:.1f}")
    
    results.append({
        "title": title,
        "old_price": old_p,
        "new_price": new_p,
        "discount_pct": pct,
        "savings_tl": savings,
        "viral_score": score,
        "url": url,
        "image_url": d.get("image_url", ""),
        "source": d.get("source", ""),
        "raw_deal": d
    })

# Puan ve indirime göre sırala
results.sort(key=lambda x: (x["viral_score"], x["savings_tl"]), reverse=True)

with open("scratch/top_scanned_deals.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\n" + "="*70)
print("🏆 EN İYİ ADAYLAR:")
print("="*70)
for i, r in enumerate(results[:10], 1):
    print(f"{i}. {r['title']}")
    print(f"   Fiyat: {r['old_price']} -> {r['new_price']} (-%{r['discount_pct']}, Net: {r['savings_tl']:.0f} TL)")
    print(f"   Viral Skor: {r['viral_score']:.1f} | Link: {r['url']}")
