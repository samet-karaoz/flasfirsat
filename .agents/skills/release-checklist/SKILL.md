---
name: release-checklist
description: "Git commit ve push öncesi yapılması zorunlu adımları içeren sürüm ve dağıtım kontrol listesi. Kod bütünlüğünü, güvenlik filtrelerini ve temiz sürüm yönetimini sağlar."
---

# Release Checklist (Sürüm ve Dağıtım Kontrol Listesi)

Bu skill, yapılan herhangi bir geliştirme veya hata düzeltmesi sonrasında kodların Git/GitHub ortamına güvenle aktarılmasını sağlayan standart prosedürdür.

---

## 1. Commit Öncesi Adımlar (Pre-Commit)

Geliştirici veya AI agent, commit oluşturmadan önce sırasıyla şu adımları tamamlamalıdır:

### 1. Sözdizimi ve Import Testi (Syntax Check)
Değiştirilen tüm Python dosyaları çalıştırılarak import hataları kontrol edilir:
```bash
python -c "import deal_bot, telegram_notifier, product_verifier; print('OK')"
```

### 2. Dosya Durum Kontrolü (git status)
```bash
git status -s
```
- Listede `.env`, `data/`, `client_secrets.json`, geçici loglar veya test medya dosyaları var mı?
- Varsa `.gitignore` kontrol edilir ve bu dosyalar depoya eklenmez.

### 3. Doğruluk ve Yasal Uyum Kontrolü
- Yapılan değişiklikler `deal-truthfulness` ve `ad-compliance-tr` kurallarına uygun mu?

---

## 2. Commit Mesaj Standartları

Commit mesajları conventional commits standardına uygun, net ve açıklayıcı olmalıdır:
- `feat:` Yeni bir özellik eklendiğinde (Örn: `feat: add Telegram approval flow`)
- `fix:` Bir hata düzeltildiğinde (Örn: `fix: correct old price strike-through alignment`)
- `refactor:` Kod yapısı iyileştirildiğinde (Örn: `refactor: modularize affiliate manager`)
- `docs:` Dokümantasyon eklendiğinde (Örn: `docs: add youtube setup guide`)

---

## 3. Push Sonrası Kontrol (Post-Push)
- Uzak sunucuya (origin main) başarılı iletildiği doğrulanır.
- Kullanıcıya yapılan ana değişiklikler ve yeni yetenekler özetlenir.
