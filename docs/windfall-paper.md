# Windfall

**A Multi-agent AI Pipeline That Rebuilds Abandoned Travel Carts Instead of Discounting Them**

COMPFEST 18 AIC · Team: 6 Eyes
Tema: AI for the Backbone of the Economy | Subtema: Smart Commerce
Fokus: Personalized Service, Customer Analysis, Sales & Marketing Optimization

Zhillan Baniaksa · Micguel Katili · Tania Ju

> **Status of this document.** This is the specification and authority #1 per
> `frontend/CLAUDE.md`. It is a faithful transcription of the submitted paper.
> Known defects are listed under [Errata](#errata) and are **not** silently
> corrected in the body — where an erratum conflicts with the body, CLAUDE.md
> records the resolved decision and implementation follows that.

---

## Abstrak

Agen perjalanan online (OTA) adalah salah satu bidang yang membuat *cart
abandonment* menjadi tantangan yang signifikan karena tingkat *cart
abandonment* berada di antara 81–90%. Hal ini terjadi karena mereka tidak
menetapkan heterogenitas profil pelanggan serta sensitivitas harga untuk setiap
traveler, sehingga strategi pemulihan konvensional yang bergantung pada
pemberitahuan generik sering kali berkinerja buruk.

Usulan kami, Windfall, membangun mesin pemulihan keranjang (*cart-recovery*)
berbasis AI yang proaktif berdasarkan arsitektur *multi-agen* yang menargetkan
traveler ke dalam kelompok pengeluaran (Value, Comfort, Premium) melalui
penalaran atas riwayat pemesanan dengan AI. Arsitektur ini terdiri atas tiga
agen yang dijalankan secara berurutan: **Classifier Agent** menentukan tingkatan
pengeluaran traveler; **Searcher Agent** mengeksekusi *rebuild ladder*, urutan
percobaan rekonstruksi *cart* dari perubahan terkecil hingga terbesar; dan
**Notification Curator Agent** menyusun pesan yang sesuai dengan tingkatan dan
keputusan yang diambil dan mengirimnya setelah persetujuan analis.

Ketiga agen tidak memanggil klien API secara langsung, melainkan melalui Model
Context Protocol (MCP) sebagai lapisan antarmuka *tool* yang terstandarisasi,
sehingga logika penalaran terpisah dari sumber data. Dengan mengintegrasikan API
*real-time* serta mekanisme *price-freeze* berbasis Hold Order, sistem
menghasilkan penawaran terpersonalisasi guna meminimalisir *cart abandonment*
tanpa mengorbankan margin mitra secara berlebihan (dengan diskon).

**Kata Kunci:** Online Travel Agency (OTA), Cart abandonment, Cart-recovery
Engine, Multi-agent System, Model Context Protocol (MCP), Artificial
Intelligence (AI), B2B Travel, Sales Optimization, Smart Commerce.

---

## 1. Latar Belakang

Industri travel online atau Online Travel Agency (OTA) mengalami tingkat *cart
abandonment* yang jauh lebih tinggi dibandingkan dengan rata-rata e-commerce,
dengan angka yang umum dikutip berada pada kisaran 81%–90%. Berdasarkan laporan
Google e-Conomy SEA, pemesanan travel online yang sukses di Indonesia mencapai
US$10,6 miliar, yang merepresentasikan hanya 10%–19% pengguna layanan OTA [4].
Oleh karena itu, pasar OTA Indonesia kehilangan *revenue volume* total sebesar
US$45,2–US$95,4 miliar setiap tahunnya.

Penyebab utamanya meliputi harga total pada akhir proses penambahan dalam *cart*
yang tidak sesuai dengan anggaran yang dimiliki traveler, biaya atau pajak yang
baru muncul di tahap akhir, serta perilaku pengguna yang memakai *cart* untuk
membandingkan harga pada tiap platform tanpa niat melakukan pembayaran saat itu
juga.

Masalah inti yang ingin diselesaikan bukan sekadar "*cart* ditinggalkan",
melainkan bahwa hampir seluruh platform memperlakukan setiap *cart* yang
ditinggalkan dengan cara yang sama berupa satu email pengingat generik untuk
semua orang, padahal alasan seseorang tidak melanjutkan *checkout* sangat
bervariasi antarindividu. Traveler dengan histori pemesanan kelas premium tidak
seharusnya diperlakukan sama dengan traveler yang sangat sensitif terhadap
harga; keduanya membutuhkan ambang notifikasi dan jenis penawaran yang berbeda
agar upaya pemulihan *cart* benar-benar efektif dan tidak terasa seperti spam.

Prinsip inti yang mendasari solusi ini:

> **"Not every abandoned travel cart needs a discount. Every cart needs to be
> rebuilt to fit all wallets."**

Pendekatan *emailing* diskon konvensional saat ini memiliki efektivitas yang
rendah: 63% konsumen mengabaikan email tanpa personalisasi dan 70% konsumen
cenderung berhenti berlangganan (*unsubscribe*) akibat kelebihan pesan pemasaran
yang tidak relevan [5, 7]. Fenomena ini bukan hanya biaya yang terbuang: dalam
pemasaran langsung, tindakan yang tidak relevan dapat menimbulkan *uplift*
negatif, yaitu pelanggan yang justru berhenti berlangganan atau *churn* akibat
pesanan yang tidak diinginkan [10].

Strategi tersebut sering kali mengandalkan notifikasi spam yang menggerus
profitabilitas, mengingat margin operasional hotel yang tipis (5%–15%) dapat
dengan mudah terkikis oleh komisi OTA (15% hingga lebih dari 30%) [2, 6].
Sebaliknya, personalisasi berbasis segmentasi profil pelanggan (RFM) terbukti
mampu meningkatkan retensi pelanggan hingga 20% dengan memposisikan interaksi
sebagai *value-driven recovery* [3]. Alih-alih memberikan diskon massal, sistem
kami menganalisis profil historis untuk menentukan kebutuhan pengguna (traveler,
klien OTA): baik itu penyusunan ulang komposisi *cart*, opsi *price-freeze*,
atau sekadar pengingat relevan tanpa diskon sama sekali.

### 1.1 Analisis Kompetitor

| Aspek | Hopper | OTA Konvensional | Windfall |
|---|---|---|---|
| Unit analisis AI | Rute (route-level) | Tidak ada / rule-based | Individu traveler |
| Metode segmentasi | Tidak membangun profil per pelanggan | Blast seragam ke seluruh cart | Penalaran AI atas histori pemesanan (RFM-informed) |
| Aksi pemulihan | Price-freeze pada produk yang sama | Kode diskon seragam | Rekonstruksi komposisi cart (rebuild ladder) |
| Arsitektur AI | Model prediksi harga tunggal | – | Multi-agent (Classifier → Searcher → Notification Curator) |
| Antarmuka tool AI | Integrasi internal tertutup | Panggilan API langsung | Model Context Protocol (MCP) |
| Monetisasi | Konsumen membayar di muka | Biaya pemasaran ditanggung OTA | Komisi hanya saat pemulihan berhasil |

Perbedaan paling substantif terletak pada unit analisis dan jenis aksi. Hopper
menjalankan prediksi harga pada level rute: seluruh pengguna yang mencari rute
CGK–NRT menerima sinyal yang pada dasarnya sama, karena sistem tidak membangun
profil historis per pelanggan. Konsekuensinya, satu-satunya aksi yang tersedia
adalah membekukan harga pada produk yang tidak berubah.

Windfall mengubah kedua dimensi tersebut. **Pertama**, unit analisisnya adalah
individu: agen AI menalar histori pemesanan traveler untuk menentukan tingkatan
pengeluarannya, sehingga ambang notifikasi bersifat adaptif per segmen
(Value ≥ 5%, Comfort ≥ 10%, Premium ≥ 15%). **Kedua**, aksinya tidak terbatas
pada harga: ketika *re-pricing* pada *cart* yang sama tidak mencukupi, sistem
menyusun ulang komposisi *cart* melalui *rebuild ladder*, misalnya menukar
tingkatan bintang hotel sambil mempertahankan destinasi dan tanggal. Kemampuan
rekonstruksi inilah yang secara harfiah menjalankan prinsip "rebuilt to fit all
wallets", dan tidak dimiliki oleh kompetitor mana pun yang hanya memodifikasi
harga atas produk yang tetap. **Ketiga**, dari sisi arsitektur, Windfall
mengadopsi pola *multi-agent* dengan MCP sebagai lapisan antarmuka *tool*
terstandarisasi. Pola ini memisahkan penalaran (*reasoning*) dari eksekusi
(*tool call*), sehingga sumber data dapat diganti tanpa mengubah *prompt* maupun
logika agen.

---

## 2. Tujuan dan Manfaat Pengembangan

### 2.1 Tujuan

- Mengembangkan mekanisme pemulihan *cart* yang menentukan jenis aksi (pengingat
  tanpa diskon, *re-pricing*, atau rekonstruksi *cart*) berdasarkan profil
  traveler, bukan menerapkan satu perlakuan seragam.
- Mengklasifikasikan traveler ke dalam tingkatan pengeluaran
  (Value/Comfort/Premium) melalui penalaran AI atas histori pemesanan, sebagai
  dasar personalisasi ambang notifikasi.
- Mengimplementasikan *rebuild ladder*: urutan upaya rekonstruksi komposisi
  *cart* dari perubahan terkecil hingga terbesar, berhenti pada percobaan
  pertama yang memenuhi ambang.
- Mengintegrasikan mekanisme *price-freeze* yang benar-benar didukung API
  maskapai (Hold Order), sehingga tenggat waktu yang ditampilkan ke pengguna
  selalu nyata.
- Menerapkan MCP sebagai lapisan antarmuka *tool* agar migrasi dari *dataset*
  statis ke sumber data *live* pasca-penyisihan tidak mengubah logika agen.

### 2.2 Manfaat

| Pihak Terkait | Manfaat |
|---|---|
| Traveler (konsumen) | Menerima penawaran yang relevan dengan kebiasaan belanja mereka, dengan tenggat waktu yang benar-benar berlaku, tanpa perlu memantau harga secara manual dan berkala. |
| Travel brand / OTA | Meminimalisir *cart abandonment*. Memperoleh lapisan pemulihan *cart* dengan biaya nol di muka (komisi hanya atas *booking* yang berhasil dipulihkan), sekaligus data analitik segmentasi pelanggan. Margin terlindungi karena diskon tidak diberikan kepada traveler yang tidak terhalang harga. |
| Windfall | Pendapatan komisi berulang dari setiap *booking* yang berhasil dipulihkan, dengan model bisnis yang selaras dengan keberhasilan mitra (*aligned incentive*). |

### 2.3 Proof of Value (PoV) dan Proof of Concept (PoC)

#### 2.3.1 Proof of Value

Nilai produk diukur melalui tiga indikator: (a) *recovery rate*, yakni proporsi
*cart* yang berhasil dipulihkan menjadi *booking*; (b) *margin preservation*,
yakni proporsi pemulihan yang tercapai tanpa pemberian diskon (melalui jalur
pengingat atau rekonstruksi *cart*); dan (c) *notification precision*, yakni
proporsi notifikasi terkirim yang menghasilkan interaksi, sebagai indikator
berkurangnya spam.

Indikator (b) merupakan diferensiator utama: pendekatan konvensional hanya dapat
memulihkan *cart* dengan mengorbankan margin, sedangkan Windfall dirancang untuk
memulihkan sebagian *cart* tanpa biaya diskon sama sekali.

Prinsip di balik indikator (b) berkorespondensi dengan *uplift modelling* dalam
pemasaran langsung, yang membedakan pelanggan yang merespons karena tindakan
dari mereka yang merespons terlepas dari tindakan tersebut [10]. Memberikan
diskon pada kelompok kedua merupakan pengorbanan margin tanpa dampak konversi;
bahkan, studi tersebut mendokumentasikan *uplift* negatif pada segmen bernilai
tinggi, di mana kampanye justru menurunkan pembelian. Windfall menargetkan hanya
traveler yang keputusannya dapat diubah oleh tindakan, sementara traveler yang
akan tetap konversi diarahkan ke jalur pengingat tanpa diskon.

Mekanisme rekonstruksi *cart* secara struktural berbeda dari pemberian diskon.
Penurunan harga yang diterima traveler bersumber dari komposisi produk, bukan
dari margin yang dikorbankan mitra OTA ketika sistem menukar hotel bintang 4
menjadi 3 pada parameter pencarian item yang sama. Dengan demikian, jalur
rekonstruksi memulihkan *cart* dengan biaya diskon nol, sementara jalur pengingat
(untuk traveler yang harga bukan penghalangnya) tidak menimbulkan biaya sama
sekali.

Biaya menjalankan *agent pipeline* perlu dibandingkan secara eksplisit dengan
biaya alternatifnya. Perbandingan yang relevan bukan dari biaya per *cart* yang
berhasil dipulihkan melainkan:

1. **Biaya:** konsumsi token per *cart* × jumlah *cart* yang diproses, berbanding dengan
2. **Penghematan:** diskon yang berhasil dihindari pada *cart* yang terpulihkan.

Mengingat tingkat peninggalan *cart* berada pada kisaran 81%–90%, sistem
memproses sejumlah besar *cart* untuk memulihkan sebagian kecil di antaranya.
Meskipun demikian, biaya inferensi per *cart* berada pada orde sen, sedangkan
satu diskon 10% pada *cart* senilai semisal IDR 27.000.000 setara dengan
pengorbanan margin sekitar IDR 2.700.000, selisih dua hingga tiga orde besaran.
Rasio ini tetap menguntungkan bahkan pada asumsi *recovery rate* yang
konservatif.

Karakteristik yang lebih menentukan adalah perbedaan skala biaya: biaya diskon
bersifat proporsional terhadap nilai *cart*, sedangkan biaya inferensi bersifat
tetap. Konsekuensinya, keunggulan biaya pendekatan ini justru menguat pada
segmen opsi barang bernilai tinggi — segmen yang paling mahal untuk dipulihkan
dengan diskon konvensional.

#### 2.3.2 Proof of Concept

Untuk tahap penyisihan, PoC dibuktikan melalui demonstrasi *end-to-end* atas
skenario traveler yang telah disiapkan, di mana sistem menunjukkan secara
transparan: klasifikasi tingkatan traveler beserta alasan penalarannya, urutan
percobaan *rebuild* yang dijalankan beserta hasil tiap percobaan, keputusan akhir
jenis aksi, pratinjau notifikasi yang dihasilkan, dan — setelah persetujuan
analis — pengiriman email yang sebenarnya. Seluruh alur berjalan dalam satu
siklus permintaan sinkron dan dapat direproduksi secara lokal melalui
`docker compose` sesuai `README.md`.

### 2.4 Batasan Ruang Lingkup Tahap Penyisihan

| Ketentuan | Implementasi pada Tahap Penyisihan |
|---|---|
| **FE:** input tunggal, tanpa dasbor analitik, tanpa otentikasi kompleks, tanpa halaman riwayat | Antarmuka satu halaman berisi daftar kartu profil traveler. Satu aksi klik pengguna memicu keseluruhan alur AI; hasilnya ditampilkan sebagai jejak penalaran dan pratinjau notifikasi. Tidak ada dasbor, sistem login, maupun halaman riwayat. |
| **BE:** hanya pemrosesan sinkron, tanpa *background jobs*, tanpa *automated data logging*, tanpa basis data terdistribusi | Seluruh *pipeline* berjalan dalam satu siklus *request/response* pada satu *endpoint* Flask. Tidak ada *scheduler*, *worker queue*, maupun basis data terdistribusi; data skenario dibaca dari berkas lokal. Tidak ada penulisan log otomatis. Sistem dijalankan melalui `docker compose`. |
| **AI:** hanya *core inference*, parameter statis saat demonstrasi, tanpa *auto-tuning*, tanpa *bulk testing*, tanpa *feedback loop* | Tiga agen berbasis Gemini menjalankan inferensi inti dengan *prompt* dan ambang yang bersifat statis (didefinisikan sebagai konstanta). Tidak ada pembaruan parameter otomatis, skrip pengujian massal, maupun mekanisme umpan balik. |

**Catatan pengiriman.** Pengiriman email dilakukan secara sinkron di dalam
permintaan persetujuan analis. Ini tetap berada di dalam ketentuan BE: tidak ada
antrean, *worker*, maupun *scheduler*. Klik persetujuan adalah konfirmasi atas
aksi yang menimbulkan efek samping, bukan input kedua yang memicu AI.

Rancangan operasional penuh (aktivasi periodik setiap N jam, penyimpanan
terdistribusi, dan pencatatan konversi) dinyatakan secara eksplisit sebagai visi
pasca-penyisihan pada Subbab 5.3, dan tidak diimplementasikan pada repositori
tahap ini.

---

## 3. Metodologi: Alur dalam Memperoleh Dataset

Dataset yang digunakan sistem terbagi menjadi dua kategori dengan sifat dan
sumber yang berbeda: data transaksional yang diambil secara sinkron saat
permintaan berjalan, dan data historis traveler untuk klasifikasi. Untuk tahap
penyisihan, seluruh parameter klasifikasi bersifat statis dan tidak memerlukan
infrastruktur basis data terdistribusi.

### 3.1 Data Transaksional (Diambil Sinkron Saat Permintaan)

- **Penawaran penerbangan:** diperoleh langsung dari Duffel API menggunakan
  *live key*, sehingga harga yang diproses adalah harga yang benar-benar dapat
  dipesan, bukan simulasi.
- **Penawaran hotel:** diperoleh melalui RapidAPI.
- **Data lokasi:** divalidasi melalui Google Places API untuk memastikan setiap
  lokasi dapat diverifikasi.
- **Waktu pengambilan:** seluruh pemanggilan API dilakukan secara sinkron di
  dalam siklus permintaan yang dipicu pengguna. Tidak terdapat mekanisme
  pengambilan ulang terjadwal pada tahap ini.

### 3.2 Data Historis Traveler untuk Klasifikasi

#### 3.2.1 Tahap 1: Penetapan skema kebutuhan

Klasifikasi tingkatan memerlukan tiga sinyal per traveler, yang dipilih karena
selaras dengan kerangka RFM [1, 3] sekaligus tersedia pada data pemesanan OTA
mana pun: (a) rata-rata total pengeluaran per *trip* (*monetary*), yang sekaligus
menjadi *baseline* pengeluaran biasa traveler `s_i` untuk perhitungan kesenjangan
anggaran pada §4.1; (b) frekuensi pemesanan historis (*frequency*); dan (c)
komposisi kualitas yang dipilih, berupa proporsi kelas premium dan rata-rata
kategori bintang hotel.

Skema klasifikasi menyertakan *campaign share*, yaitu proporsi pengeluaran
historis traveler pada produk berdiskon terhadap total pengeluaran sebagai
proksi sensitivitas harga, selain RFM konvensional. Fitur tersebut memungkinkan
pemisahan *price-sensitive traveler* dan *price-insensitive traveler* pada
tingkatan *monetary* yang sama, sejalan dengan kerangka *extended RFM* yang
menunjukkan bahwa dimensi tambahan seperti *campaign share* mengidentifikasi
pelanggan yang sensitif terhadap kampanye [11]. Traveler dengan *campaign share*
rendah pada tingkatan Premium menandakan bahwa harga bukan penghalang konversi.

#### 3.2.2 Tahap 2: Pemilihan sumber referensi

Distribusi nilai untuk ketiga sinyal tersebut dikalibrasi dengan merujuk pada
karakteristik *dataset* publik bertema pemesanan perjalanan yang tersedia di
Kaggle, khususnya *Hotel Booking Demand* (Antonio, de Almeida & Nunes, 2019) yang
memuat 31 variabel dan lebih dari 119.000 observasi pemesanan, termasuk *average
daily rate* (ADR), lama menginap, tipe pelanggan, dan status pembatalan [8, 9].
Rujukan ini digunakan untuk memastikan bentuk distribusi (rentang nilai,
kemencengan, proporsi antar segmen) yang dihasilkan bersifat realistis dan tidak
arbitrer.

#### 3.2.3 Tahap 3: Konstruksi dataset seed

Berdasarkan karakteristik distribusi tersebut, disusun *dataset seed* statis
berisi profil traveler sintetis beserta riwayat pemesanannya. Penggunaan data
sintetis dipilih secara sadar atas dua pertimbangan: pertama, data pemesanan riil
bersifat *personally identifiable* sehingga penggunaannya menimbulkan persoalan
privasi; kedua, ketentuan tahap penyisihan mensyaratkan parameter statis,
sehingga *dataset* terkendali justru lebih sesuai daripada tarikan data *live*.

Arketipe skenario demonstrasi diselaraskan dengan segmen empiris pada literatur
*extended RFM*: traveler *price-sensitive* (*campaign share* tinggi) merujuk pada
segmen oportunis yang hanya membeli saat diskon, sementara traveler premium
dengan *campaign share* rendah merujuk pada segmen loyal bernilai tinggi yang
pembeliannya independen dari kampanye [11].

#### 3.2.4 Tahap 4: Kalibrasi ambang persentil

Ambang tingkatan tidak ditetapkan sebagai angka nominal tetap, melainkan sebagai
persentil terhadap distribusi *dataset seed* (indikatif: persentil ≤ 30 sebagai
Value, 31–80 sebagai Comfort, > 80 sebagai Premium). Pendekatan persentil dipilih
agar model tetap valid ketika diterapkan pada pasar atau mata uang berbeda
pasca-kompetisi. Nilai hasil kalibrasi kemudian dibekukan sebagai konstanta
statis dalam kode, sesuai ketentuan parameter statis pada saat demonstrasi.

Secara formal, untuk traveler `i` dengan sinyal *monetary* `m_i`, peringkat
persentil terhadap distribusi *dataset seed* didefinisikan sebagai
`q_i = F_M(m_i)`, dan tingkatan ditetapkan secara *piecewise*:

```
        ⎧ Value     q_i ≤ 0,30
T_i  =  ⎨ Comfort   0,30 < q_i ≤ 0,80
        ⎩ Premium   q_i > 0,80
```

Ambang minimum penghematan per tingkatan dinyatakan sebagai
`τ(Value) = 0,05`, `τ(Comfort) = 0,10`, `τ(Premium) = 0,15`. Ambang *campaign
share* dinyatakan sebagai `c* = 0,25`.

Nilai titik potong (0,30 dan 0,80), `τ`, dan `c*` merupakan **konstanta
kalibrasi, bukan hasil derivasi matematis**; notasi ini berfungsi agar aturan
bersifat presisi dan dapat direproduksi, dan seluruh konstanta dibekukan sesuai
ketentuan parameter statis pada tahap penyisihan.

Model persentil ini berperan sebagai rujukan kalibrasi dan jalur *cold-start*;
Classifier Agent menalar tingkatan dalam kerangka ambang ini namun dapat
memasukkan sinyal yang tidak tertangkap oleh persentil tunggal (lintasan
pengeluaran, *campaign share*, konteks *cart*), sehingga klasifikasi tetap berupa
penalaran, bukan pencocokan tabel.

#### 3.2.5 Tahap 5: Penanganan cold start

Untuk traveler tanpa histori pemesanan, sistem menggunakan sinyal dari *cart*
yang sedang berjalan sebagai proksi sementara, yaitu kelas penerbangan dan
kategori bintang hotel yang dipilih pada pemesanan tersebut.

*Campaign share* untuk traveler *cold start* bernilai **null** dan tidak pernah
dikarang. Karena `c_i` tidak terdefinisi, konjungsi pada §4.1 tidak dapat
dievaluasi. **Pengecualian:** *rebuild ladder* tetap dijalankan atas tingkatan
proksi, karena rekonstruksi tidak mengorbankan margin sama sekali. Yang tidak
dapat dibenarkan oleh *cold start* adalah aksi yang memakan margin, dan tahap
penyisihan tidak menerbitkan aksi semacam itu.

### Tabel: Ringkasan Karakteristik Dataset

| Aspek | Data Transaksional | Data Historis Traveler |
|---|---|---|
| Sumber | Duffel, RapidAPI, Google Places | *Dataset seed* sintetis, dikalibrasi terhadap karakteristik *dataset* publik Kaggle |
| Sifat | Riil dan dapat dipesan | Statis dan terkendali |
| Waktu akses | Sinkron saat permintaan berjalan | Dibaca dari berkas lokal saat permintaan berjalan |
| Alasan pemilihan | Membuktikan harga bukan simulasi | Menghindari isu privasi; memenuhi syarat parameter statis |

---

## 4. Metodologi: Alur Pengembangan Model Tiap Fitur

Setiap fitur dikembangkan melalui alur yang konsisten: definisi kebutuhan user →
desain PoC, *product value map*, dan *fit* → kontrak input/output →
implementasi *design wireframe* dan *high fidelity* → implementasi *frontend* →
*backend development* → pengujian terhadap data nyata dari API terkait →
*refinement*.

Prinsip pembagian tanggung jawab yang dianut: **penalaran diserahkan kepada agen
AI, sedangkan eksekusi panggilan API yang bersifat transaksional tetap
deterministik.** Pemisahan ini dipilih karena keputusan yang menyangkut transaksi
finansial (kelayakan Hold Order, perhitungan selisih harga) harus dapat diaudit
dan direproduksi secara pasti, sementara penilaian yang bersifat kontekstual
(tingkatan traveler, susunan pesan) justru merupakan wilayah yang tepat bagi
penalaran AI.

### Tabel: Alur Pengembangan Fitur

| Fitur | Status | Alur Pengembangan Singkat |
|---|---|---|
| Parsing permintaan | Existing | Desain skema JSON terstruktur → *prompt engineering* pada Gemini API → pengujian terhadap variasi format teks bebas pengguna. |
| Pencarian flight + hotel | Existing | Integrasi ke Duffel API dan hotel API dengan *live key* → *mapping response* ke struktur data internal → validasi tidak ada data *mock*/*hardcoded*. |
| Penyusunan itinerary | Existing | *Prompt design* pada Gemini untuk kurasi lokasi → *grounding* terhadap Google Places API untuk mencegah halusinasi. |
| Classifier Agent | To be implemented | Desain kontrak keluaran terstruktur (tingkatan + alasan penalaran) → *prompt design* agar Gemini menalar histori pemesanan alih-alih sekadar menerapkan tabel pencarian → kalibrasi ambang persentil terhadap *dataset seed* → desain jalur *cold-start* → pengujian terhadap kombinasi profil traveler. |
| Searcher Agent (rebuild ladder) | To be implemented | Definisi urutan percobaan rekonstruksi dari perubahan terkecil ke terbesar → implementasi *re-query* deterministik per percobaan → perhitungan selisih harga → evaluasi terhadap ambang per tingkatan → penghentian pada percobaan pertama yang memenuhi ambang. |
| Mekanisme freeze/hold | To be implemented | Pemeriksaan *field* `payment_requirements` dan `price_guarantee_expires_at` pada *offer* Duffel → pemeriksaan kelayakan Hold Order untuk maskapai yang didukung → *fallback pre-authorization* (disimulasikan dan dilabeli eksplisit pada tahap ini) → penanganan error `price_changed` sebagai jalur *repricing*, bukan kegagalan. |
| Notification Curator Agent | To be implemented | Desain kontrak keluaran (subjek, isi email, isi WhatsApp, label CTA) → *prompt design* agar pesan menyebutkan jenis rekonstruksi yang dilakukan, bukan urgensi generik → penyesuaian *tone* per tingkatan → pratinjau, lalu pengiriman email setelah persetujuan analis. |
| Lapisan MCP | To be implemented | Definisi skema *tool* (`read_traveler_history`, `search_flights`, `search_hotels`, `check_hold_eligibility`) → implementasi server MCP yang membungkus klien API yang sudah ada → pengujian bahwa penggantian sumber data di balik *tool* tidak mengubah *prompt* agen. |

### 4.1 Rebuild Ladder

*Rebuild ladder* merupakan mekanisme yang menerjemahkan prinsip "rebuilt to fit
all wallets" menjadi operasi konkret. Percobaan dijalankan berurutan dari
perubahan terkecil, dan berhenti pada percobaan pertama yang memenuhi ambang
tingkatan traveler, sehingga hasil akhir tetap sedekat mungkin dengan pesanan
awal.

Secara formal, *ladder* merupakan urutan percobaan `a_1, a_2, …, a_K`,
masing-masing menghasilkan *cart* kandidat berharga `p_k` terhadap harga awal
`p_0`, dengan penghematan relatif `δ_k = (p_0 − p_k) / p_0`. Sistem memilih
percobaan pertama yang memenuhi ambang tingkatan:

```
k* = min{ k ∈ {1, …, K} : δ_k ≥ τ(T_i) }
```

Apabila tidak ada percobaan yang memenuhi (`{k : δ_k ≥ τ(T_i)} = ∅`), sistem
menempuh jalur alternatif atau pengingat. Operator `min` memformalkan prinsip
"berhenti pada perubahan terkecil yang mencukupi", sehingga hasil akhir tetap
sedekat mungkin dengan pesanan awal.

#### Tabel: Urutan Percobaan Rebuild Ladder

| Urutan | Percobaan | Yang Berubah | Status Penyisihan |
|---|---|---|---|
| 01 | Re-pricing *cart* yang sama | Tidak ada; hanya harga di-*query* ulang | Diimplementasikan |
| 02 | **Lateral** | Hotel setara: bintang, tanggal, dan kawasan tetap sama | Diimplementasikan |
| 03 | Penukaran tingkatan hotel | Bintang hotel turun satu tingkat; destinasi dan tanggal tetap | Diimplementasikan |
| 04 | Pergeseran tanggal | Tanggal bergeser dalam rentang terbatas; destinasi tetap | Roadmap |
| 05 | Kombinasi | Penukaran hotel dan pergeseran tanggal | Roadmap |
| — | Tanpa rekonstruksi yang memenuhi | Jalur alternatif atau pengingat tanpa diskon | Diimplementasikan |

**Lateral hanya menyentuh hotel.** Penerbangan dipertahankan pada seluruh
percobaan: Hold Order Duffel dipegang terhadap satu *offer* penerbangan
tertentu, sehingga menukar penerbangan akan membatalkan jaminan harga yang
justru menjadi alasan keberadaan *freeze*. Substitusi hotel juga bersifat netral
terhadap margin. Penukaran penerbangan pada kabin yang sama termasuk Subbab 5.3.

Percobaan lateral hanya ditampilkan apabila penghematannya memenuhi `τ`. Kasus
"menemukan opsi, namun tidak layak ditampilkan" harus tetap dapat tercapai, atau
prinsip menahan diri berhenti menjadi keluaran yang nyata.

#### Keputusan jenis aksi

Keputusan jenis aksi tidak ditentukan oleh selisih harga semata, melainkan oleh
dua sinyal independen: sensitivitas harga (*campaign share* `c_i`) dan
kesenjangan anggaran *cart* terhadap pengeluaran biasa traveler,
`g_i = (p_0 − s_i) / s_i`. Jalur rekonstruksi hanya ditempuh apabila **kedua**
kondisi terpenuhi:

```
        ⎧ rebuild ladder           c_i ≥ c*  ∧  g_i > 0
D_i  =  ⎨
        ⎩ pengingat, tanpa diskon  selainnya
```

di mana `c*` adalah ambang *campaign share* (`c* = 0,25`). Ekspresi ini
memformalkan prinsip inti Windfall: intervensi harga hanya dilakukan ketika
traveler terbukti sensitif harga **dan** *cart* benar-benar melampaui
anggarannya. Traveler Premium dengan *campaign share* rendah (`c_i < c*`) — yang
harga bukan penghalangnya — jatuh ke jalur pengingat secara struktural, bukan
sebagai pengecualian. *Campaign share* tinggi semata tidak memicu diskon; yang
memicu adalah konjungsi keduanya, sehingga margin mitra tidak tergerus oleh
diskon kepada traveler yang akan tetap konversi.

#### Empat keluaran

`rebuild` · `lateral` · `reminder` · `alternative`

Keluaran tanpa diskon dinamai **reminder**, bukan *hold*, untuk menghindari
tabrakan istilah dengan Hold Order (mekanisme *price-freeze* maskapai).

---

## 5. Metodologi: Alur Integrasi Model ke Environment Kode

*Basecode* menggunakan Python (Flask) sebagai *backend*. Mengikuti ketentuan
bahwa arsitektur *backend* wajib hanya sampai pada pemrosesan interaksi sinkron,
bab ini dipisahkan menjadi dua: Subbab 5.1–5.2 memaparkan implementasi yang
benar-benar dibangun untuk tahap penyisihan, sedangkan Subbab 5.3 memaparkan
visi arsitektur penuh yang berada di luar cakupan tahap ini.

### 5.1 Arsitektur Multi-agent dan Lapisan MCP

Sistem terdiri atas tiga agen berbasis Gemini yang dijalankan secara berurutan,
ditambah satu lapisan MCP sebagai antarmuka *tool*.

| Agen | Masukan | Keluaran | Peran AI |
|---|---|---|---|
| **Classifier Agent** | Histori pemesanan traveler, *cart* yang ditinggalkan | Tingkatan (Value/Comfort/Premium) + alasan penalaran | Menalar tingkatan dari pola histori, bukan mencocokkan tabel |
| **Searcher Agent** | Tingkatan, *cart* awal, hasil *re-query* API | Tingkat *rebuild* yang berhasil, komposisi baru, selisih harga | Menilai kecukupan tiap percobaan terhadap ambang tingkatan |
| **Notification Curator Agent** | Tingkatan, tingkat *rebuild*, komposisi baru | Subjek, isi email, isi WhatsApp, label CTA | Menyusun pesan yang menjelaskan rekonstruksi yang dilakukan; pengiriman dilakukan setelah persetujuan analis |

Ketiga agen tidak memanggil klien API secara langsung, melainkan melalui *tool*
yang diekspos via MCP: `read_traveler_history`, `search_flights`,
`search_hotels`, dan `check_hold_eligibility`.

`create_hold` **berada di luar cakupan**: pemanggilan tersebut merupakan operasi
tulis nyata terhadap inventaris maskapai dan tidak boleh dijalankan selama
demonstrasi. Pemeriksaan kelayakan bersifat *read-only* dan aman dijalankan
sinkron.

Manfaat utamanya bersifat arsitektural: pada tahap penyisihan
`read_traveler_history` membaca *dataset seed* statis dari berkas lokal,
sedangkan pasca-penyisihan *tool* yang sama dapat dialihkan ke sumber data *live*
tanpa mengubah *prompt* maupun logika penalaran agen mana pun. MCP di sini
berfungsi sebagai kontrak antarmuka, bukan layanan tambahan yang berjalan
mandiri; seluruh pemanggilan tetap berlangsung sinkron di dalam siklus permintaan
yang sama.

### 5.2 Implementasi Tahap Penyisihan

#### 5.2.1 Pemicu

Keseluruhan alur dipicu oleh satu aksi klik pengguna pada antarmuka (memilih
kartu profil traveler), bukan oleh penjadwal. Tidak terdapat *background job*,
*worker queue*, maupun *scheduler* pada repositori tahap ini.

Pengiriman email dipicu oleh aksi persetujuan yang terpisah dan eksplisit.
Menelusuri beberapa traveler tidak mengirim satu pun email.

#### 5.2.2 Struktur modul

Modul baru ditambahkan sebagai *blueprint* terpisah, dipanggil secara sinkron
oleh satu *endpoint*:

- `classifier_agent` — klasifikasi tingkatan traveler
- `searcher_agent` — eksekusi *rebuild ladder* dan perhitungan selisih harga
- `notification_curator` — penyusunan pratinjau notifikasi
- `hold_manager` — pemeriksaan kelayakan *price-freeze*
- `mcp_tools` — definisi skema *tool* dan pembungkus klien API

#### 5.2.3 Penyimpanan

Data skenario traveler dan konfigurasi ambang disimpan sebagai berkas lokal
(JSON), bukan basis data terdistribusi. Tidak terdapat penulisan log otomatis;
hasil tiap pemanggilan dikembalikan langsung dalam *response* API.

#### 5.2.4 Alur end-to-end (sinkron)

```
Pengguna memilih kartu traveler
        |
        v
POST /api/recovery/run  -- satu siklus request/response
        |
        +- MCP: read_traveler_history          (dataset seed lokal)
        +- Classifier Agent   -> tingkatan + alasan penalaran
        +- Searcher Agent     -> rebuild ladder
        |     +- MCP: search_flights, search_hotels   (per percobaan)
        +- MCP: check_hold_eligibility         (read-only)
        +- Notification Curator Agent -> subjek, isi, CTA
        |
        v
Response: jejak penalaran, keputusan, pratinjau notifikasi
        |
        v
Analis menyetujui  --> POST /api/recovery/send  --> email terkirim
```

Seluruh langkah berada dalam masa hidup satu permintaan HTTP. Sistem dapat
dijalankan secara lokal melalui `docker compose`.

### 5.3 Visi Arsitektur Pasca-Penyisihan

Rancangan berikut **tidak diimplementasikan** pada tahap penyisihan:

- **Orchestrator Agent** yang mengaktifkan *pipeline* secara periodik setiap N jam.
- **Migrasi penyimpanan** ke basis data terkelola dengan koleksi `carts`,
  `tier_config`, dan `notifications_log` untuk audit dan evaluasi konversi.
- **Peralihan `read_traveler_history`** ke profil historis dinamis per traveler.
  Karena *tool* MCP telah menjadi kontrak antarmuka sejak tahap penyisihan,
  peralihan ini tidak mengubah logika agen.
- **Perluasan rebuild ladder** ke pergeseran tanggal, kombinasi, dan penukaran
  penerbangan pada kabin yang sama.
- **Perluasan kewenangan agen** melalui *tool-calling* MCP.
- **Agent-as-a-service** bagi beberapa mitra OTA.
- **Pengukuran uplift** memerlukan kelompok kontrol: sampel traveler yang
  **sengaja tidak diberi** tindakan sebagai pembanding [10].
- **Tampilan batch / fleet** untuk memproses banyak *cart* sekaligus.

---

## 6. Kesimpulan

Produk ini menjawab masalah yang lebih spesifik dibanding "*cart abandonment* itu
buruk": masalah sebenarnya adalah perlakuan yang seragam terhadap pelanggan yang
berbeda kebutuhan dan sensitivitas harganya. Melalui arsitektur *multi-agent*,
Windfall memisahkan tiga keputusan yang selama ini dikompresi menjadi satu
tindakan generik: siapa dan bagaimana perilaku traveler tersebut (Classifier
Agent), apa yang harus diubah pada *cart*-nya (Searcher Agent dengan *rebuild
ladder*), dan bagaimana hal tersebut dikomunikasikan (Notification Curator
Agent).

Kontribusi utama yang membedakan pendekatan ini terletak pada kemampuan
rekonstruksi komposisi *cart*, bukan sekadar modifikasi harga. Kompetitor
terdekat hanya dapat membekukan atau menurunkan harga atas produk yang tidak
berubah; Windfall dapat menyusun ulang isi *cart* agar sesuai kemampuan bayar,
dan justru menahan diri dari pemberian diskon ketika profil traveler menunjukkan
harga bukan penghalangnya. Kemampuan menahan diri inilah yang secara langsung
melindungi margin mitra.

Seluruh mekanisme dibangun di atas infrastruktur yang telah terintegrasi pada
*basecode* (Duffel, RapidAPI, Google Places, Gemini, Flask), sehingga
pengembangan bersifat inkremental. Penyederhanaan untuk tahap penyisihan berupa
pemicu sinkron, penyimpanan lokal, dan *dataset* historis statis dilakukan secara
sadar dan dinyatakan eksplisit pada Subbab 2.4.

---

## Daftar Pustaka

1. Barilliance. "RFM Analysis: The Ultimate Guide." https://www.barilliance.com/rfm-analysis/
2. Cloudbeds. "How Online Travel Agencies (OTAs) Work." 2026.
3. FasterCapital. "RFM Analysis: How RFM Analysis Can Enhance Your Customer Segmentation Optimization Strategy." 2025.
4. Google. "Indonesia's Online Travel Market Eyes US$17 Billion Future." Web in Travel.
5. Mailmend. "Email Personalization Statistics." 2026.
6. VantaInsights. "Hotel Profit Margins." 2026.
7. Optimove. "Consumer Marketing Fatigue Report." 2025.
8. N. Antonio, A. de Almeida, dan L. Nunes. "Hotel booking demand datasets." *Data in Brief*, vol. 22, hlm. 41-49, 2019. DOI: 10.1016/j.dib.2018.11.126
9. J. Mostipak. "Hotel Booking Demand." Kaggle.
10. P. Rzepakowski dan S. Jaroszewicz. "Uplift modeling in direct marketing." *Journal of Telecommunications and Information Technology*, vol. 2, hlm. 43-50, 2012.
11. T. Ozcan. "Customer segmentation using an extended RFM model and clustering algorithms in e-commerce." *Journal of Theoretical and Applied Electronic Commerce Research*, vol. 21, no. 5, hlm. 142, 2026. DOI: 10.3390/jtaer21050142

---

## Errata

Applied in this transcription. **The submitted PDF still carries every defect
below** and has not been regenerated from this markdown.

| # | Defect in the PDF | Applied here |
|---|---|---|
| 1 | Tabel 1.6 has no lateral rung | Lateral added as rung 02 |
| 2 | `c*` used in section 4.1 but never given a value | Stated as 0,25 in 3.2.4 and 4.1 |
| 3 | Section 3.2.3 cites `[10]` for an extended-RFM claim | Corrected to `[11]` (Ozcan) |
| 4 | Section 5.3 reads *"tidak sengaja diberi tindakan"*, inverting the holdout definition | Corrected to *"sengaja tidak diberi"* |
| 5 | Tabel 1.5 says *"rendering preview tanpa pengiriman aktual"* | Rewritten as preview then approval then send |
| 6 | Gambar 5.1 labels the first agent "Organizer Agent" | Classifier Agent throughout |
| 7 | Agent naming drifts three ways | Canonical: **Notification Curator Agent** |
| 8 | Section 3.2.5 silent on cold-start `campaignShare` | Stated as null, with the ladder exception |
| 9 | "traveler" and "wisatawan" used interchangeably | Standardised on **traveler** |
| 10 | Section 2.3.1 argues value in USD while the product prices in IDR | Converted to IDR |
| 11 | Section 3.1 names Hotels.com; the code calls Tripadvisor via RapidAPI | Generalised to "RapidAPI" pending the provider decision |
