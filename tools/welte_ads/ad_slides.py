"""Slides for selected Welte ads, one topic each, in the deck's format."""

import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path

BOX_W, BOX_H = 900, 800
TOTAL_ADS = 195
EDITION = " Diese und die folgenden Anzeigen nach https://anz.welte225.org, abgerufen am 10.11.2026."


@dataclass(frozen=True)
class AdSlide:
    ad: str
    blob: str
    size: tuple[int, int]
    topic: str
    heading: str
    ads_with_topic: int
    quote: str
    alt: str
    source: str
    notes: str

    def image_box(self) -> tuple[int, int]:
        w, h = self.size
        scale = min(BOX_W / w, BOX_H / h)
        return round(w * scale), round(h * scale)

    def html(self, edition_note: str = "") -> str:
        w, h = self.image_box()
        caption = f"{self.source}.{edition_note}"
        notes = f"{self.notes}\nMotiv „{self.topic}“ in {self.ads_with_topic} von {TOTAL_ADS} Anzeigen der Edition: https://anz.welte225.org/topic/{self.topic}/"
        return "\n".join([
            f'<section id="anz-{self.ad}" data-transition="fade" style="background:#ffffff;color:#000000;'
            "font-family:'IBM Plex Mono', 'Courier New', monospace;padding:64px 64px 200px;display:flex;"
            'flex-direction:row;gap:64px;align-items:center">',
            f'<div style="width:{BOX_W}px;display:flex;justify-content:center">'
            f'<img src="/_blob/{self.blob}" alt="{escape(self.alt)}" style="width:{w}px;height:{h}px;object-fit:contain"></div>',
            '<div style="flex:1;display:flex;flex-direction:column;gap:32px">',
            "<h2 style=\"font-family:'IBM Plex Mono', 'Courier New', monospace;font-size:48px;font-weight:500;"
            f'line-height:1.1">{escape(self.heading)}</h2>',
            f'<p style="font-size:32px;line-height:1.35"><i>{escape(self.quote)}</i></p>',
            f'<p style="font-size:24px;line-height:1.35">in {self.ads_with_topic} von {TOTAL_ADS} Anzeigen</p>',
            "</div>",
            f'<p style="position:absolute;left:64px;bottom:36px;width:1792px;font-size:24px;line-height:1.35">{caption}</p>',
            f"<aside>{escape(notes, quote=False)}</aside>",
            "</section>",
        ])


SLIDES = [
    AdSlide(
        "ad009", "a5d9b8d111244363d66e04d57d742a86", (2000, 1546), "not_mechanical", "Kunst, nicht Mechanik", 25,
        "„Das Reproduktionsklavier hat nichts gemein mit mechanischen Spielapparaten wie Pianola, Phonola etc.“",
        "Textanzeige „Ein musikalisches Weltwunder“ mit Stimmen von Pianisten, Allgemeine Zeitung, München 1905",
        "Anzeige „Ein musikalisches Weltwunder“, in: <i>Allgemeine Zeitung</i> (München), 27.12.1905, S. 4, "
        "https://www.digitale-sammlungen.de/de/view/bsb00085796_01057_u001?page=4",
        "Die früheste Anzeige der Edition (Alleinvertretung Alfred Schmid Nachf., München). Weiter: „es handelt sich also nicht um ein Surrogat, "
        "sondern um eine vollwertige Vertretung.“ Und: „Wenn das Reproduktionsklavier vor 50 Jahren existiert hätte, könnten wir auch heute noch "
        "dem Spiel der grossen Meister wie Liszt, Rubinstein, Bülow lauschen und daran lernen.“ Rechts Stimmen von d'Albert, Ansorge, Busoni, "
        "Carreño, Dohnányi, Gabrilowitsch, Grünfeld, Kleeberg, Lamond, Nikisch, Pugno, Reisenauer, Weingartner.\n"
        "Definition in der Edition: „The instrument is set apart from mechanical, automatic or player-piano playing: it is human, artistic, "
        "‚not a surrogate‘, or the prejudice that it is mechanical is refuted.“",
    ),
    AdSlide(
        "ad116", "cef8f374e63dc2b9826338cda3fcd295", (1428, 2000), "faithful_reproduction", "Getreue Wiedergabe", 98,
        "„La maravillosa fidelidad con que la WELT-MIGNON recoge todos los detalles de la ejecución […] y la exactitud con que los reproduce“",
        "Fotografie: Josef Hofmann am Aufnahmeflügel, umgeben von vier Personen, darunter Text der Anzeige",
        "Anzeige „Josef Hofmann impresionando en la WELT-MIGNON“, in: <i>Social</i> (La Habana), April 1923, Nr. 4, S. 7, "
        "https://archive.org/details/SocialVolIIINo4Abril1923/page/n4/mode/1up",
        "Bildunterschrift der Anzeige: „Josef Hofmann impresionando en la WELT-MIGNON la célebre Overture de Tannhauser“. Die Personen um ihn "
        "nennt die Anzeige nicht. Der Text verbindet Treue und Unterricht: „para que discípulos y profesores se den cabal cuenta de la manera "
        "individual de interpretar de cada uno de los grandes ‚virtuosi‘ de la época.“ Händler: John L. Stowers, Havanna.\n"
        "Das häufigste Motiv der Sammlung, und genau das, was die Varianten zwischen den Kopien in Frage stellen.",
    ),
    AdSlide(
        "ad039", "e69f1b78d7f56a18a0528f3e712cc74f", (1394, 2000), "artists_hear_themselves", "Die Künstler hören sich selbst", 19,
        "„When Paderewski listens to his own Playing – not while he sits at the piano, but comfortably established in an easy chair like other hearers“",
        "Textanzeige „When Paderewski listens to his own Playing“, New York Tribune 1913",
        "Anzeige „When Paderewski listens to his own Playing“, in: <i>New York Tribune</i> (New York), 7.12.1913, S. 3, "
        "https://chroniclingamerica.loc.gov/lccn/sn83030214/1913-12-07/ed-1/seq-3",
        "Weiter: „The wonderful Welte-Mignon autographic records of playing by Paderewski, Hofmann, Carreño and other great artists have all "
        "been heard by the musicians themselves and signed by them as true and actual autographs of their playing.“ Vgl. das Rollenetikett "
        "„Gespielt von“ mit Griegs Unterschrift (Deutsches Museum, Rolle 1275).\n"
        "Definition: „The artists vouch for their own recordings: they hear or recognise their own playing, are deceived by it, sign the "
        "rolls as autographs …“",
    ),
    AdSlide(
        "ad197", "b511c04ed6216578db5d3f7e85ea260d", (1022, 1419), "masters_at_home", "Die großen Pianisten zu Hause", 62,
        "„Ihre Gäste sind ganz entzückt wenn das WELTE-MIGNON ton- und klanggetreu das Meister-Spiel der ersten Klavierkünstler in Ihrem Heim erklingen läßt“",
        "Zeichnung: Gäste in Abendkleidung hören einem Flügel zu, der ohne Spieler spielt",
        "Anzeige „Ihre Gäste sind ganz entzückt …“, in: <i>Sport im Bild</i> (Berlin), Nr. 29, 1923, S. 950, "
        "https://anno.onb.ac.at/cgi-content/anno-plus?aid=sib&amp;datum=1923&amp;page=950",
        "Inserent: M. Welte & Söhne, Freiburg i. B., „Fabrik pneumatischer Musikwerke“. Am Flügel sitzt niemand.\n"
        "Definition: „The famous pianists can be heard in your own home or on your own piano, at any time, as often as you wish, at your command“.",
    ),
    AdSlide(
        "ad104", "5d7358bbb825c4332c7ec4ba304afe13", (1117, 2000), "phantom_hands", "Geisterhände", 17,
        "„Watch the keys of your piano moving, though no one sits before it!“",
        "Anzeige mit Tanzszene, Flügel und einer kleinen Vignette mit Händen auf einer Klaviatur: When Phantom Fingers Play",
        "Anzeige „Rhythmic Beat of a Gaucho Dance – When Phantom Fingers Play“, in: <i>London Evening Advertiser</i> (London, Ontario), "
        "10.12.1924, S. 8, https://www.canadiana.ca/view/oocihm.N_00257_19241210/8",
        "Mason & Risch Welte-Mignon Reproducing Piano, Händler in London, Ontario. Die Vignette rechts neben dem Text: „These are the Phantom "
        "Hands of a thousand immortal pianists …“. Aus derselben Reihe „When Phantom Fingers Play“ in der Edition auch ad105 (The Free Press, 1924).\n"
        "Vgl. den Titel der Dissertation „Grünfelds Geist“.\n"
        "Definition: „The absent performer appears as a phantom or spirit: ghostly or semi-transparent hands and figures, keys moving with no one "
        "seated, the artist summoned at will“.",
    ),
    AdSlide(
        "ad102", "68bc09f9baf544b8fdb169a9b8a685e6", (1082, 714), "education", "Bildung und Studium", 18,
        "„… wurde soeben vom k. k. österreichischen Ministerium für Kultus und Unterricht zu pädagogischen Zwecken für das Wiener Konservatorium angekauft.“",
        "Anzeige mit Abbildung des Welte-Mignon-Vorsetzers, Rigasche Rundschau 1909",
        "Anzeige „Das Reproduktions-Piano Welte-Mignon … Wiener Konservatorium“, in: <i>Rigasche Rundschau</i> (Riga), Nr. 51, 4./17.3.1909, S. 4, "
        "https://www.europeana.eu/item/9200303/BibliographicResource_3000059905820",
        "Weiter: „Ein glänzender Beweis für die unerreichten Leistungen unseres Instrumentes in künstlerischer Beziehung.“ Händler: Jul. Heinr. "
        "Zimmermann, Riga. Abgebildet ist der Vorsetzer (Schrankmodell).\n"
        "Vgl. die Allgemeine Zeitung 27.12.1905 (Diss., Einleitung): „daß den Studierenden die Vortragsart eines Meisters zu jeder Zeit vorgeführt werden kann“.\n"
        "Definition: „The instrument serves learning and teaching: conservatories, students, studying an interpretation by repeating it.“",
    ),
    AdSlide(
        "ad077", "e7cd0d488e1643745b814eaf93ac1cf2", (531, 928), "composers_own_works", "Komponisten spielen eigene Werke", 7,
        "„Grieg: Schmetterling, Vøglein, Brudefølget drager forbi. Samtlige spillet af Edv. Grieg.“",
        "Programm einer Mignon-Soirée in Kristiania, Dezember 1907, mit Grieg, Paderewski, Carreño, Dohnányi, Schnabel, Wendling",
        "Anzeige „Mignon Soirée“, in: <i>Aftenposten</i> (Kristiania), 11.12.1907, S. 2, "
        "https://www.nb.no/items/URN:NBN:no-nb_digavis_aftenposten_null_null_19071211_48_730_1",
        "Vorführung bei Grøndahls Flygel & Pianolager, Kristiania, 11. und 12. Dezember 1907, drei Monate nach Griegs Tod (4.9.1907). "
        "Die drei Grieg-Stücke sind die Welte-Rollen 1275, 1277 und 1276, laut Freiburger Rollenverzeichnis aufgenommen am 17.4.1906 in Leipzig; "
        "1275 liegt im Instrument des Deutschen Museums. Außerdem: Paderewski spielt sein Menuett (Rolle 1263).\n"
        "Definition: „The ad stresses that composers themselves recorded, or are heard playing, their own compositions.“ Überleitung zur Liste.",
    ),
]


if __name__ == "__main__":
    out = Path(sys.argv[1])
    for s in SLIDES:
        edition_note = EDITION if s is SLIDES[0] else ""
        (out / f"anz-{s.ad}.html").write_text(s.html(edition_note) + "\n", encoding="utf-8")
        print(f"anz-{s.ad}", s.image_box())
