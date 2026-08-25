# Naskah Demo — Recovering Cart (Ria Lavenia → Nasywa Namira)

Naskah untuk dibacakan sambil menjalankan console Windfall. Angka di sini bukan
karangan: semuanya keluaran nyata `pipeline.run()` atas seed `travelers.json`
(mode fixture, inference Gemini aktif). Kalau angka di layar berbeda dari
naskah, layar yang benar — jangan bacakan angka lama.

Landasan paper: §3.2.4 (tier persentil), §4.1 (rebuild ladder + gate),
§2.3 (nol margin dikorbankan), §5.2.4 (satu request sinkron).

Durasi target: ±3 menit 30 detik untuk dua traveler.

---

## 0. Pembuka — kenapa bagian ini ada (±20 detik)

> **[Layar: halaman queue, "Abandoned carts awaiting a decision"]**

"Ini antrean *abandoned cart* — keranjang yang ditinggalkan traveler sebelum
bayar. Perhatikan kartunya: tidak ada tier, tidak ada campaign share. Itu
disengaja. Semua penilaian itu adalah *keluaran* pipeline, bukan sesuatu yang
sudah tertulis di kartu sebelum agen berjalan. Kalau sudah tercetak di kartu,
demo ini cuma membacakan jawaban yang sudah disiapkan.

Saya akan jalankan dua traveler yang sengaja berlawanan hasilnya. Yang pertama
dapat rekonstruksi harga. Yang kedua tidak dapat apa-apa — dan justru itu yang
paling ingin saya tunjukkan."

---

## 1. Ria Lavenia — jalur rebuild (±1 menit 40 detik)

> **[Klik kartu Ria Lavenia. Tiga avatar agen mulai bangun satu per satu.]**

"Satu klik, satu request. Classifier, Searcher, Notification Curator berjalan
berurutan di dalam satu request sinkron — tidak ada antrean, tidak ada worker di
belakang layar. Seluruh jejak penalarannya dikembalikan di satu response."

### 1a. Classifier

> **[Layar: kartu Classifier terbuka — Tier Value, threshold 5%]**

"Ria punya 3 pemesanan, pengeluaran biasa 6 juta rupiah. Terhadap distribusi
seed, persentilnya jatuh di **tier Value**, dan tier menentukan ambang
penghematan tau — untuk Value, **5 persen**.

Yang penting: tier ini dihitung deterministik dulu sebagai *prior*, baru
Classifier Agent boleh menggesernya satu tingkat dengan alasan tertulis. Di
kasus ini agen setuju dengan prior. Jadi kalau suatu saat agen menggeser tier,
pergeserannya kelihatan dan bisa dibantah — bukan keputusan yang tak terlihat."

### 1b. Gate — dua sinyal, bukan satu

> **[Layar: Campaign share 46% · Delta anggaran +14% · gate OPENED]**

"Sebelum menyentuh harga, sistem menanyakan dua hal yang independen.

Pertama, apakah traveler ini memang sensitif harga: *campaign share*-nya
**46 persen**, di atas ambang c-bintang 25 persen. Kedua, apakah keranjangnya
memang melampaui anggaran dia sendiri: cart 6.840.000 versus pengeluaran biasa
6 juta — **14 persen di atas**.

Keduanya terpenuhi, jadi gerbang **terbuka**. Ini konjungsi, bukan salah satu.
Campaign share tinggi saja tidak memicu diskon."

### 1c. Searcher — rebuild ladder

> **[Layar: tabel "Rebuild attempts", tiga baris]**

"Sekarang *rebuild ladder*. Percobaan dijalankan dari perubahan paling kecil,
dan berhenti di percobaan pertama yang mencukupi.

- **Percobaan 1 — cart yang sama, di-*re-price*.** Tidak ada yang berubah, harga
  di-query ulang: 6.696.360. Delta **2,1 persen**. Di bawah ambang.
- **Percobaan 2 — *lateral*.** Hotel setara: tetap 4 bintang, tetap Marina Bay,
  tanggal sama — Pan Pacific Singapore. 6.580.080, delta **3,8 persen**. Masih di
  bawah ambang, jadi opsi ini **tidak ditawarkan**. Sistem menemukannya, tapi
  menahan diri.
- **Percobaan 3 — turun satu bintang.** Hotel Boss, 3 bintang, area dan tanggal
  tetap: 6.073.920. Delta **11,2 persen** — **lolos**.

Ladder berhenti di sini. Percobaan 4 dan 5 di paper — pergeseran tanggal dan
kombinasi — tidak dijalankan, karena sudah cukup.

Dan penerbangannya tidak pernah disentuh di ketiga percobaan. Hold Order Duffel
dipegang terhadap satu offer penerbangan tertentu; menukar penerbangan justru
membatalkan jaminan harga yang jadi alasan hold itu ada."

> **[Sorot catatan Searcher pada baris ketiga]**

"Perhatikan catatan agennya sendiri: turun dari Fullerton Bay ke Hotel Boss itu
penurunan kualitas yang terasa, meskipun lolos ambang. Agen mengatakannya, tidak
menyembunyikannya."

### 1d. Outcome + hold

> **[Layar: OutcomeCard "REBUILD OFFER" · panel Price freeze eligibility]**

"Hasilnya: **rebuild**. Traveler hemat **766.080 rupiah**, dan — ini angka yang
saya minta diperhatikan — **margin yang dikorbankan: nol rupiah**. Tidak ada
diskon yang diberikan. Penghematannya datang dari menyusun ulang komposisi
inventaris, bukan dari memotong margin mitra.

Kelayakan *price freeze*: eligible untuk ANA, harga penerbangan dijamin sampai
7 November. Tarif hotel tetap dihitung ulang saat pembayaran — dan itu
dituliskan apa adanya di email, bukan dijanjikan lebih."

### 1e. Draf notifikasi

> **[Layar: Notification previews — email + WhatsApp]**

"Notification Curator menulis pesannya dalam Bahasa Indonesia dan menyebut **apa
yang benar-benar diubah** — hotel diganti, penerbangan dan tanggal tetap — bukan
urgensi generik semacam 'buruan, stok terbatas'.

Dan ini masih **draf**. Menjalankan pipeline hanya menulis; mengirim butuh klik
kedua dari analis. Analis yang membuka enam traveler untuk membaca penalarannya
tidak boleh diam-diam mengirim enam email."

---

## 2. Nasywa Namira — jalur reminder (±1 menit 10 detik)

> **[Kembali ke queue, klik kartu Nasywa Namira]**

"Traveler kedua. Cart-nya jauh lebih besar: Emirates kelas bisnis Dubai–London,
menginap di The Savoy, total **64.480.000 rupiah**. Secara naluri komersial,
inilah cart yang paling ingin diselamatkan."

### 2a. Classifier

> **[Layar: Tier Premium, threshold 15%]**

"8 pemesanan, pengeluaran biasa 62 juta, 75 persen di kabin premium, rata-rata 5
bintang. **Tier Premium**, ambang tau **15 persen** — sengaja lebih tinggi,
karena hemat 5 persen bukan alasan yang masuk akal untuk membuka kembali cart
traveler Premium."

### 2b. Gate — tertutup

> **[Layar: Campaign share 9% · Delta anggaran +4% · gate CLOSED]**

"Sekarang dua sinyal yang tadi.

Cart-nya memang **4 persen di atas** pengeluaran biasanya — sumbu kedua
terpenuhi. Tapi *campaign share*-nya **9 persen**, jauh di bawah ambang 25
persen. Traveler ini secara historis membayar harga penuh.

Artinya harga **bukan penghalangnya**. Gerbang **tertutup**."

### 2c. Yang tidak terjadi

> **[Layar: tabel Rebuild attempts kosong · OutcomeCard "REMINDER — NO DISCOUNT"]**

"Dan lihat: **rebuild ladder-nya tidak dijalankan sama sekali**. Bukan
dijalankan lalu hasilnya ditolak — memang tidak pernah dimulai. Nol percobaan.

Hasilnya **reminder**: pengingat tanpa diskon. Penghematan nol, margin
dikorbankan nol, **margin mitra utuh**.

Inilah yang saya maksud di awal. Traveler Premium dengan campaign share rendah
jatuh ke jalur pengingat secara **struktural** — karena rumusnya menuntut kedua
kondisi terpenuhi — bukan karena ada aturan pengecualian yang ditempelkan
belakangan. Sistem ini menahan diri pada cart 64 juta, dan itu keputusan yang
benar."

### 2d. Notifikasi

> **[Layar: preview email Nasywa]**

"Emailnya pun tidak menyinggung harga sama sekali. Perjalanannya masih
tersimpan, detailnya sama persis. Itu saja. Tidak ada 'khusus untuk Anda', tidak
ada diskon yang dikarang."

---

## 3. Penutup bagian ini (±20 detik)

> **[Layar: sandingkan dua hasil, atau kembali ke queue]**

"Dua cart, dua hasil yang berlawanan, dari satu rumus yang sama — tanpa aturan
khusus untuk salah satunya.

Yang murah dapat rekonstruksi dengan penghematan 11 persen dan nol margin
dikorbankan. Yang mahal tidak dapat apa-apa, karena harga memang bukan
masalahnya.

Itulah arti 'rebuilt to fit all wallets': bukan membagikan diskon, tapi menyusun
ulang keranjang hanya ketika penyusunan ulang itu memang jawabannya."

---

## Catatan produksi

- **Nama.** Di seed, traveler pertama bernama **Ria Lavenia** (`wf-01`), bukan
  "Lavenia Kharissa". Nasywa Namira adalah `wf-03`. Kalau namanya mau diganti,
  ubah `backend/recovery/seed/travelers.json` dulu — jangan hanya di ucapan,
  karena nama itu muncul di layar dan di isi email.
- **Angka yang harus disebut persis:** 46% / +14% / 2,1% / 3,8% / 11,2% /
  Rp766.080 / Rp0 margin — dan 9% / +4% / 0 percobaan / Rp0.
- **Mode.** Rekam dengan `WINDFALL_FIXTURES=1` plus `WINDFALL_LIVE_INFERENCE=1`:
  harga direplay dari capture sehingga durasi stabil, tapi penalaran benar-benar
  dari Gemini. Console akan melabeli kedua sumbu itu terpisah. Pastikan
  `GEMINI_API_KEY` terisi — tanpa itu pipeline menolak jalan (503), bukan
  memalsukan inference.
- **Jeda.** Beri hening ±1 detik setelah "margin yang dikorbankan: nol rupiah"
  dan setelah "gerbang tertutup". Dua kalimat itu yang paling ingin diingat.
- **Jangan** menyebut keluaran tanpa diskon sebagai "hold". Namanya **reminder** —
  "hold" sudah dipakai untuk price-freeze maskapai.
