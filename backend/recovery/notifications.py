"""
notifications.py — Notification Curator copy.

Traveler-facing copy is Indonesian, formal-but-warm second person, addressing
the traveler as Anda. Analyst-facing chrome stays English. Numbers are
Indonesian-formatted on both sides.

The boundary this module defends: the outcome arrives already decided. The
curator writes prose for a Decision it is handed; it can neither choose nor
overturn one. Templates below are the deterministic fallback and the fixture
path, and notification_curator.py swaps Gemini in against exactly these shapes.

House rules, from the design system and kept because they are right: no emoji,
no manufactured urgency, and no deadline unless a carrier guaranteed the fare.
"""
from __future__ import annotations

from typing import Optional

from .formatting import idr
from .schemas import (
    AbandonedCart, Decision, HoldStatus, NotificationDraft, Outcome,
)


def _first_name(full_name: str) -> str:
    return full_name.strip().split(" ")[0]


def _stay(cart: AbandonedCart) -> str:
    return "{} ({} bintang) di {}".format(
        cart.hotel.name, cart.hotel.stars, cart.hotel.area)


def _trip(cart: AbandonedCart) -> str:
    return "{} - {} bersama {}".format(
        cart.flight.origin, cart.flight.destination, cart.flight.carrier)


def _deadline_line(hold: HoldStatus) -> Optional[str]:
    """A deadline appears only when a carrier actually guaranteed the fare."""
    if not hold.may_render_deadline:
        return None
    return ("Harga penerbangan dijamin maskapai sampai {}. Tarif hotel masih "
            "dihitung ulang saat pembayaran.").format(hold.expires_at)


def _swapped_hotel(decision: Decision) -> str:
    for attempt in decision.attempts:
        if attempt.cleared and attempt.hotel is not None:
            return "{} ({} bintang)".format(attempt.hotel.name, attempt.hotel.stars)
    return "penginapan pengganti"


def draft(cart: AbandonedCart, traveler_name: str, decision: Decision,
          hold: HoldStatus, alternative_label: Optional[str] = None,
          alternative_desc: Optional[str] = None) -> NotificationDraft:
    name = _first_name(traveler_name)
    city = cart.hotel.city
    outcome = decision.outcome

    if outcome == Outcome.REMINDER:
        return _reminder(name, city, cart)
    if outcome == Outcome.LATERAL:
        return _lateral(name, city, cart, decision, hold)
    if outcome == Outcome.REBUILD:
        return _rebuild(name, city, cart, decision, hold)
    if outcome == Outcome.ALTERNATIVE:
        return _alternative(name, city, cart, decision,
                            alternative_label, alternative_desc)
    raise ValueError("no copy for outcome " + repr(outcome))


def _reminder(name, city, cart) -> NotificationDraft:
    """
    No discount, no saving, nothing to claim. The tone carries the decision:
    this traveler was not blocked by price, so the message must not invent a
    reason to act. Restraint is stated plainly, never left as an empty message.
    """
    return NotificationDraft(
        subject="Perjalanan {} Anda masih tersimpan".format(city),
        body_paragraphs=[
            "Halo {}, perjalanan Anda ke {} masih kami simpan - {}, dengan "
            "menginap di {}.".format(name, city, _trip(cart), _stay(cart)),
            "Semuanya persis seperti yang Anda tinggalkan. Kami tidak mengubah "
            "harga maupun detailnya, dan tidak ada penawaran yang perlu Anda "
            "kejar. Kapan pun waktunya terasa tepat, pemesanan bisa "
            "dilanjutkan dalam beberapa ketukan.",
            "Jika rencana Anda berubah, tidak ada yang perlu dilakukan.",
        ],
        whatsapp=(
            "Halo {}, perjalanan Anda ke {} masih tersimpan - {}, menginap di "
            "{}. Tidak ada yang berubah dan tidak ada yang perlu diklaim; siap "
            "kapan pun Anda siap.".format(name, city, _trip(cart), cart.hotel.name)
        ),
        cta_label="Lihat kembali perjalanan Anda",
        channel_note="Tidak ada diskon diberikan. Margin mitra utuh.",
    )


def _lateral(name, city, cart, decision, hold) -> NotificationDraft:
    hotel = _swapped_hotel(decision)
    saved = idr(decision.saving_idr)
    paras = [
        "Halo {}, perjalanan Anda ke {} masih tersimpan - {}.".format(
            name, city, _trip(cart)),
        "Kami menemukan pilihan menginap lain di kawasan dan tanggal yang "
        "sama, dengan kelas bintang yang sama seperti pilihan Anda: {}. "
        "Totalnya {} lebih ringan, dan tidak ada satu pun bagian perjalanan "
        "yang diturunkan kelasnya.".format(hotel, saved),
    ]
    line = _deadline_line(hold)
    if line:
        paras.append(line)
    paras.append(
        "Kalau Anda lebih suka pilihan semula, pilihan itu juga masih ada dan "
        "tidak kami ubah sama sekali.")
    return NotificationDraft(
        subject="Perjalanan {} Anda, dengan pilihan menginap yang lebih ringan".format(city),
        body_paragraphs=paras,
        whatsapp=(
            "Halo {}, untuk perjalanan {} Anda kami menemukan penginapan kelas "
            "bintang yang sama di kawasan dan tanggal yang sama, {} lebih "
            "ringan. Tidak ada yang diturunkan kelasnya.".format(name, city, saved)
        ),
        cta_label="Lihat pilihan yang kami temukan",
    )


def _rebuild(name, city, cart, decision, hold) -> NotificationDraft:
    hotel = _swapped_hotel(decision)
    saved = idr(decision.saving_idr)
    paras = [
        "Halo {}, perjalanan Anda ke {} masih tersimpan - {}, dengan rencana "
        "menginap di {}.".format(name, city, _trip(cart), _stay(cart)),
        "Kami menyusun ulang satu bagian saja agar totalnya {} lebih ringan: "
        "penerbangan, tanggal, dan kawasannya tetap sama, yang berubah hanya "
        "penginapannya menjadi {}.".format(saved, hotel),
    ]
    line = _deadline_line(hold)
    if line:
        paras.append(line)
    paras.append(
        "Jika yang semula tetap yang Anda inginkan, versi itu masih utuh dan "
        "bisa Anda pilih kembali kapan saja.")
    return NotificationDraft(
        subject="Perjalanan {} Anda, disusun ulang agar pas".format(city),
        body_paragraphs=paras,
        whatsapp=(
            "Halo {}, perjalanan {} Anda masih tersimpan. Kami menemukan cara "
            "menjaganya nyaris sama persis dengan total {} lebih ringan - "
            "tanggal dan kawasan tetap, penginapannya berubah ke {}.".format(
                name, city, saved, hotel)
        ),
        cta_label="Lihat perjalanan yang disusun ulang",
    )


def _alternative(name, city, cart, decision, label, desc) -> NotificationDraft:
    label = label or "perjalanan lain"
    desc = desc or "dengan tanggal yang sama"
    return NotificationDraft(
        subject="{} belum pas - tapi {} mungkin iya".format(city, label),
        body_paragraphs=[
            "Halo {}, Anda sempat melihat perjalanan ke {} - {}. Kami sudah "
            "mencoba menyusunnya ulang, tetapi tidak ada versi yang menurut "
            "kami benar-benar sepadan untuk Anda.".format(name, city, _trip(cart)),
            "Daripada memaksakannya, ini satu gagasan lain untuk rentang "
            "tanggal yang sama: {}, {}, dengan total {}. Ini perjalanan yang "
            "berbeda, bukan versi turunan dari yang tadi.".format(
                label, desc, idr(decision.final_total_idr)),
            "Masih ingin ke {}? Tidak masalah - keranjang Anda yang semula "
            "tetap tersimpan.".format(city),
        ],
        whatsapp=(
            "Halo {}, kami belum menemukan versi perjalanan {} yang terasa "
            "sepadan untuk Anda. Untuk tanggal yang sama ada {} - {}. "
            "Keranjang semula tetap tersimpan.".format(name, city, label, desc)
        ),
        cta_label="Lihat perjalanan ke {}".format(label),
    )
