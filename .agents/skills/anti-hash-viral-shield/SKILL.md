---
name: anti-hash-viral-shield
description: "Instagram Reels ve YouTube Shorts algoritmalarının üretilen videoları kopya/otomasyon olarak algılamasını önleyen pHash/MD5 özgünlük kalkanı, mikro renk/süre varyasyonu ve mobil cihaz üstveri (metadata) enjeksiyonu rehberi."
---

# Anti-Hash Viral Shield (Algoritmik Özgünlük ve Spam Koruması Kalkanı)

Instagram Reels ve YouTube Shorts algoritmaları, aynı meme şablonunu kullanan videoları `pHash` (algısal görüntü özeti), `MD5` dosya özeti ve FFmpeg kodlayıcı imzası üzerinden tarar. Bu skill, her üretilen videonun algoritma gözünde **%100 benzersiz, organik bir mobil cihaz çekimi** olarak görünmesini sağlar.

---

## 1. Görüntü ve Kare Sayısı Özgünleştirme (`split_composer.py`)

1. **Rastgele Milisaniye Kırpma (`rnd_trim`):**
   - Her render işleminde meme videosunun süresinden `0.15s` ile `0.40s` arasında rastgele bir milisaniye kırpılır (`duration = raw_duration - rnd_trim`). Böylece her videonun toplam kare sayısı (frame count) ve dosya boyutu benzersiz olur.
2. **Mikro Renk ve Kontrast Varyasyonu (`eq` filtresi):**
   - İnsan gözünün fark edemeyeceği düzeyde rastgele parlaklık (`-0.012..+0.012`), doygunluk (`0.985..1.025`) ve kontrast (`0.990..1.015`) değişimi uygulanır. Bu işlem karelerin `pHash` imzasını tamamen değiştirir.
3. **İlk 1 Saniye Dinamik Mikro Punch-In Zoom:**
   - Videonun ilk 1 saniyesinde `1.05x -> 1.00x` yumuşak zoom uygulanarak hem izleyiciyi videoda tutan görsel kanca oluşturulur hem de statik kare tespiti aşılır.

---

## 2. Temiz Başlık ve Mobil Cihaz Üstverisi (Metadata Spoofing)

FFmpeg'in varsayılan `Lavf` / `libx264` otomasyon imzaları `-map_metadata -1` ve `+bitexact` bayraklarıyla silinir; yerine gerçek bir Android telefon (`Xiaomi Redmi Note 11 Pro`, Android 13, `mp42` brand) üstverisi enjekte edilir:
```text
-map_metadata -1 -fflags +bitexact -flags:v +bitexact -flags:a +bitexact
-brand mp42
-metadata com.android.version=13
-metadata com.android.manufacturer=Xiaomi
-metadata com.android.model="Redmi Note 11 Pro"
```
