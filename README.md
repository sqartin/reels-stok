# Reels Stok ☁️

Instagram Reels videolarını **bilgisayar kapalıyken bile** otomatik paylaşan bulut sistemi.

Videolar bilgisayarda üretilir ve bu deponun [**stok**](../../releases/tag/stok) sürümüne yüklenir.
GitHub Actions her 30 dakikada bir kontrol eder ve sıradaki videoyu Instagram'da paylaşır.

## Nasıl çalışır

```
Bilgisayar (açıkken)                  GitHub (her zaman)
────────────────────                  ──────────────────
Video üretir ──► "stok"a yükler ──►   stok (en fazla 100 video)
                                          │
                        30 dakikada bir: son paylaşımdan 80 dk geçti mi?
                                          │ evet
                                          ▼
                        en eski videoyu Instagram'a Reel olarak paylaşır
                        ve stoktan siler
```

- **Paylaşım aralığı:** yaklaşık 1,5 saat (GitHub zamanlayıcısı bazen 10-30 dk gecikebilir).
- **Stok:** her video bir `.mp4` ve aynı adlı bir `.txt` (Instagram açıklaması) dosyasından oluşur.
- **Çift paylaşım yok:** paylaşımı sadece bu depo yapar; bilgisayar yalnızca stok yükler.

## Dosyalar

| Dosya | Görevi |
|---|---|
| `.github/workflows/paylas.yml` | 30 dakikada bir çalışan GitHub Actions zamanlayıcısı |
| `bulut_paylas.py` | Son paylaşım zamanını kontrol eder, stoktan videoyu indirir, Instagram'a yükler, stoktan siler |
| `kalp.txt` | Bilgisayarın günlük güncellediği dosya. GitHub, 60 gün hareketsiz kalan depolarda zamanlayıcıyı kapattığı için bunu engeller |

## Gizli ayarlar (Secrets)

Instagram bilgileri kodda **yer almaz**; deponun şifreli **Settings → Secrets and variables → Actions** bölümünde durur:

| Secret | Açıklama |
|---|---|
| `IG_TOKEN` | Instagram Graph API erişim token'ı |
| `IG_ID` | Instagram işletme/içerik üreticisi hesap kimliği |

## Elle kullanım

- **Hemen kontrol et / paylaş:** Actions → *Reels paylas* → **Run workflow**
  (son paylaşımdan 80 dakika geçmediyse bekler, paylaşmaz).
- **Paylaşım aralığını değiştir:** `bulut_paylas.py` içindeki `ARALIK_DK` değeri (dakika).
- **Durdur:** Actions → *Reels paylas* → **⋯ → Disable workflow**.
- **Stoğu gör:** [Releases → stok](../../releases/tag/stok).

## Sorun giderme

| Belirti | Neden / çözüm |
|---|---|
| Çalışma loglarında `Stok bos.` | Bilgisayar uzun süredir kapalı; açınca stok kendiliğinden dolar |
| `API hatasi (190)` | Instagram token'ı geçersiz; yeni token alıp `IG_TOKEN` secret'ını güncelle |
| `Son paylasim X dk once, bekleniyor.` | Normal; aralık dolmadı |
| Zamanlanmış çalışmalar hiç başlamıyor | 60 gün hareketsizlik; Actions sekmesinden workflow'u yeniden etkinleştir |
