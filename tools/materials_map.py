# -*- coding: utf-8 -*-
"""Voorstel per materiaal uit de twaalf xls-bestanden.

MAP: ruwe naam uit het xls -> canonieke naam.  Namen die naar dezelfde
canonieke naam wijzen, worden één materiaal (dubbels, spelling, Frans/Engels).

INFO: canonieke naam -> (categorie, piramideniveau, opmerking)
piramide 0=Top 1=Top-heart 2=Heart 3=Heart-base 4=Base
Een opmerking betekent: dit is een gok of een keuze die nakijken verdient.
"""

MAP = {
    # ---- spelling, Frans/Engels, dubbels ----
    "Alcohol Phenylethylique": "Phenylethyl Alcohol",
    "Phenylethyl Alcohol": "Phenylethyl Alcohol",
    "Phenylpropylic Alcohol": "Phenylpropyl Alcohol",
    "Alpha Damascone": "Damascone Alpha",
    "Damascone Alpha": "Damascone Alpha",
    "BETA Damascone": "Damascone Beta",
    "BETA Ionone": "Ionone Beta",
    "Ionone Beta": "Ionone Beta",
    "Ionone PURE": "Ionone Pure",
    "Ambrox": "Ambroxan",
    "Ambroxan": "Ambroxan",
    "Ambrox DL": "Ambrox DL",
    "B.h.t": "BHT",
    "BHT": "BHT",
    "Basil OIL": "Basil Oil",
    "Basilic": "Basil Oil",
    "Benzyl Acet": "Benzyl Acetate",
    "Benzyl acetate": "Benzyl Acetate",
    "Bergamote": "Bergamot Oil",
    "Bergamote oil": "Bergamot Oil",
    "Bergamote Substitute": "Bergamot Substitute",
    "C 12 MNA Aldehyde": "Aldehyde C12 MNA",
    "C 14 Aldehyde": "Aldehyde C14",
    "Cadamome oil": "Cardamom Oil",
    "Carot Seed": "Carrot Seed Oil",
    "Celeri oil": "Celery Oil",
    "Cigalis (giv)": "Kephalis",
    "Cinnamon Leaves": "Cinnamon Leaf Oil",
    "CIS 6 Nonenol": "Cis-6-Nonenol",
    "Cis Jasmone": "Cis-Jasmone",
    "Cis-3-hexenol": "Cis-3-Hexenol",
    "Hexenol Cis 3": "Cis-3-Hexenol",
    "Cis-3-hexenyl acetate": "Cis-3-Hexenyl Acetate",
    "Hexenyl Cis 3 Acetate": "Cis-3-Hexenyl Acetate",
    "Cis-3-hexenyl salicylate": "Cis-3-Hexenyl Salicylate",
    "Hexenyl Cis 3 Salicylate": "Cis-3-Hexenyl Salicylate",
    "Ciste Labdanum Absolute OIL": "Labdanum Absolute",
    "Citronellol": "Citronellol",
    "Citronnellol": "Citronellol",
    "Clary Sage": "Clary Sage Oil",
    "Clary Sage oil": "Clary Sage Oil",
    "Coriander": "Coriander Oil",
    "Coriander oil": "Coriander Oil",
    "Cyprus OIL": "Cypress Oil",
    "Ectragol": "Estragole",
    "Estragol": "Estragole",
    "Estragon": "Tarragon Oil",
    "Encens Resinoid": "Frankincense Resinoid",
    "Ethyl Linalol": "Ethyl Linalool",
    "Ethyl linalool": "Ethyl Linalool",
    "Ethylvanillin": "Ethyl Vanillin",
    "Vanillin": "Vanillin",
    "Vanilline": "Vanillin",
    "Eugenol": "Eugenol",
    "Iso Eugenol": "Isoeugenol",
    "Isoeugenol": "Isoeugenol",
    "FIR Balsam Absolute": "Fir Balsam Absolute",
    "Fleur D'oranger 1103": "Orange Flower 1103",
    "Gaiacwood oil": "Guaiacwood Oil",
    "Galbanum OIL": "Galbanum Oil",
    "Gamma Methylionone": "Methyl Ionone Gamma",
    "Methylionone Gamma": "Methyl Ionone Gamma",
    "Methylionone Total": "Methyl Ionone Total",
    "Geranium Egypt": "Geranium Egypt Oil",
    "Geranium Egypt OIL": "Geranium Egypt Oil",
    "Hydroxycitronellal": "Hydroxycitronellal",
    "Hydroxycitronnellal": "Hydroxycitronellal",
    "Hydroxy": "Hydroxycitronellal",
    "Isobutylquinolein": "Isobutyl Quinoline",
    "Isobutylquinoleine": "Isobutyl Quinoline",
    "Isobutymquinoleine": "Isobutyl Quinoline",
    "Isobutavan(quest)": "Isobutavan",
    "Isobornylcyclohexanol": "Isobornyl Cyclohexanol",
    "Juniper Berries OIL": "Juniper Berry Oil",
    "Junniper Berries": "Juniper Berry Oil",
    "Lavander": "Lavender Oil",
    "Lavender OIL": "Lavender Oil",
    "Lavandin Super": "Lavandin Super Oil",
    "Lavandin Super oil": "Lavandin Super Oil",
    "Lavandin Green Absolute": "Lavandin Absolute",
    "Lemon": "Lemon Oil",
    "Lemon OIL": "Lemon Oil",
    "Lemon oil California": "Lemon Oil",
    "Linalol": "Linalool",
    "Linalool": "Linalool",
    "Lonalool": "Linalool",
    "Linalol Oxyde": "Linalool Oxide",
    "Linalyl Acet": "Linalyl Acetate",
    "Linalyl acetate": "Linalyl Acetate",
    "Madarin oil": "Mandarin Oil",
    "Mandarin": "Mandarin Oil",
    "Mandarine": "Mandarin Oil",
    "Tangerin OIL": "Tangerine Oil",
    "MATE Absolute OIL": "Mate Absolute",
    "Melisflor (firm)": "Melisflor",
    "Menthe Chine": "Cornmint Oil",
    "Methyl Octin Carbonate": "Methyl Octine Carbonate",
    "Musc Ambrette Substitute": "Musk Ambrette Substitute",
    "MUSC Ketone": "Musk Ketone",
    "Nutmeg OIL": "Nutmeg Oil",
    "Orange oil Florida": "Orange Oil",
    "Patchouly": "Patchouli Oil",
    "Patchouly OIL": "Patchouli Oil",
    "Patchouly DM": "Patchouli Oil",
    "Petit Grain Citronnier": "Petitgrain Citronnier",
    "Phenylacétic Aldehyde": "Phenylacetic Aldehyde",
    "Phenylethyl Phenylacetate": "Phenylethyl Phenylacetate",
    "Phenyletrhyl Phrnylacetate": "Phenylethyl Phenylacetate",
    "Rosemary": "Rosemary Oil",
    "Rosemary OIL": "Rosemary Oil",
    "Sandalwood oil": "Sandalwood Oil",
    "Sandalwood (firm)": "Sandalwood Firmenich",
    "Terpenyl Acetate": "Terpinyl Acetate",
    "Veltol Plus": "Ethyl Maltol",
    "Veltol Plus (= Ethyl Maltol)": "Ethyl Maltol",
    "Vetyver oil": "Vetiver Oil",
    "Vetyver Java oil": "Vetiver Java Oil",
    "Vetyveryle Acetate": "Vetiveryl Acetate",
    "Ylang OIL": "Ylang Ylang Oil",
    "Ylang Ylang": "Ylang Ylang Oil",
    "Cassis Base 345 F": "Cassis Base 345",
    "Civet Liquid (dl)": "Civet Liquid",
    "Sylvester PINE": "Scotch Pine",
    "Ethyl Acetyl Acetate": "Ethyl Acetoacetate",
    "Anethol": "Anethole",
    "Spearmint": "Spearmint Oil",
    "Clove oil": "Clove Oil",
    "Cumin oil": "Cumin Oil",
    "Eucalyptus OIL": "Eucalyptus Oil",
    "Pepper oil": "Pepper Oil",
    "Rose de Mai": "Rose de Mai Absolute",
    "Galbanum oil": "Galbanum Oil",
    "Tonalide": "Tonalid",
    "ISO E Super": "Iso E Super",
    "Allyl amyl glycolate": "Allyl Amyl Glycolate",
    "Amyl salicylate": "Amyl Salicylate",
    "Benzyl salicylate": "Benzyl Salicylate",
    "Hexyl salicylate": "Hexyl Salicylate",
    "Isoamyl salicylate": "Isoamyl Salicylate",
    "Isobutyl salicylate": "Isobutyl Salicylate",
    "Isobornyl acetate": "Isobornyl Acetate",
    "Styrallyl acetate": "Styrallyl Acetate",
    "Ethylene brassylate": "Ethylene Brassylate",
    "Benzoin Resinoid": "Benzoin Resinoid",
    "Costus Oliffac": "Costus Oliffac",
    "Pomme Oliffac": "Pomme Oliffac",
    "Animalys 1745": "Animalys 1745",
    "Lilial Osyrol": "Lilial",
    "Osyrol": "Osyrol",
    # --- correcties uit het nagekeken werkblad (MI, 07/09/2026) ---
    "Cortex Aldehyde": "Phenoxyacetaldehyde",
    "Ganolid": "Tonalid",
    "Irival": "Orris Givco",
    "Jasmin 1103": "Jasmin 1103 (Roure Bertrand base)",
    "Leafarome": "Liffarome",
    "Lemoral": "Melonal",
    "Musc T": "Ethylene Brassylate",
    "Sylvester Oakmoss": "Oakmoss",
    # --- materialen uit de twee bases Althenol en Jasmin 231 ---
    "Vetyverol": "Vetiverol",
    "Methylionone": "Methyl Ionone",
    "Rose de Mai  68 oil": "Rose de Mai 68",
    "Jasmin Absolute type": "Jasmin Absolute Type",
    "Ylang extra": "Ylang Extra",
    "C 8 Aldehyde": "Aldehyde C8",
    "C 16 Aldehyde": "Aldehyde C16",
    "Alpha ionone": "Ionone Alpha",
    "Paracresol": "Para-Cresol",
    "Benzoin resinoid": "Benzoin Resinoid",
    # zelfde stof, CAS 101-86-0, IFRA-standaard 040 alpha-hexyl cinnamic aldehyde
    "Jasmonal": "Jasmonal H",
    # --- materialen uit de base Rose de Mai 68 ---
    "Phenylethyl alcohol": "Phenylethyl Alcohol",
    "Geranyle Acetate": "Geranyl Acetate",
    "Rhodinol Bourbon": "Rhodinol Bourbon",
    "\u0152illet 35": "Oeillet 35",
    # --- materialen uit de base Oeillet 35 ---
    "Heliotropin": "Heliotropine",
    "Ylang extra oil": "Ylang Extra",
    "Cinnamon oil": "Cinnamon Oil",
    "Iris Butter": "Iris Butter",
    "Rose orient oil type": "Rose Orient Type",
    "Reseda Body (iff)": "Reseda Acetal",
}


# categorie, piramide, opmerking
INFO = {
    "Adoxal":                    ("Aldehydes", 2, ""),
    "Aldehyde C12 MNA":          ("Aldehydes", 0, ""),
    "Aldehyde C14":              ("Fruits", 3, "perzik-lacton, in feite gamma-undecalacton"),
    "Allyl Amyl Glycolate":      ("Fruits", 2, ""),
    "Allyl Cyclohexyl Propionate": ("Fruits", 1, ""),
    "Althenol":                  ("Bases & replacers", 4, ""),
    "Ambrettolide":              ("Musks", 4, ""),
    "Ambroxan":                  ("Woody - amber", 4, "Ambrox en Ambroxan samengevoegd"),
    "Ambrox DL":                 ("Woody - amber", 4, "apart gehouden van Ambroxan"),
    "Amyl Salicylate":           ("Flowers - spicy", 1, ""),
    "Anethole":                  ("Fresh", 0, ""),
    "Animalys 1745":             ("Animalic", 4, "basis, samenstelling onbekend"),
    "Anisic Aldehyde":           ("Flowers - white", 2, ""),
    "Bacdanol":                  ("Woody - sandal", 4, ""),
    "Basil Oil":                 ("Herbal - Green", 0, ""),
    "Benzoin Resinoid":          ("Balsamic/coumarinic", 4, ""),
    "Benzyl Acetate":            ("Flowers - white", 0, ""),
    "Benzyl Salicylate":         ("Flowers - white", 4, ""),
    "Bergamot Oil":              ("Citrus", 0, ""),
    "Bergamot Substitute":       ("Bases & replacers", 0, ""),
    "BHT":                       ("Additives", None, "antioxidant, geen geurbijdrage"),
    "Bourgeonal":                ("Flowers - green", 3, ""),
    "Brahmanol":                 ("Woody - sandal", 4, ""),
    "Calone":                    ("Fresh", 1, ""),
    "Canthoxal":                 ("Flowers - white", 2, ""),
    "Cardamom Oil":              ("Spices", 0, ""),
    "Carrot Seed Oil":           ("Earthy", 3, ""),
    "Cashmeran":                 ("Musks", 4, ""),
    "Cassis Base 345":           ("Fruits", 0, "basis"),
    "Celery Oil":                ("Herbal - Green", 2, ""),
    "Cinnamic Alcohol":          ("Spices", 3, ""),
    "Cinnamon Leaf Oil":         ("Spices", 2, ""),
    "Cis-3-Hexenol":             ("Herbal - Green", 2, ""),
    "Cis-3-Hexenyl Acetate":     ("Herbal - Green", 0, ""),
    "Cis-3-Hexenyl Salicylate":  ("Herbal - Green", 4, ""),
    "Cis-6-Nonenol":             ("Fresh", 0, "meloen-groen"),
    "Cis-Jasmone":               ("Flowers - white", 2, ""),
    "Citral":                    ("Citrus", 0, ""),
    "Citronellol":               ("Flowers - red", 1, ""),
    "Civet Liquid":              ("Animalic", 4, ""),
    "Clary Sage Oil":            ("Herbal - Green", 1, ""),
    "Clove Oil":                 ("Spices", 2, ""),
    "Coriander Oil":             ("Spices", 0, ""),
    "Cornmint Oil":              ("Fresh", 0, "Menthe Chine"),
    "Costus Oliffac":            ("Animalic", 4, "basis"),
    "Coumarin":                  ("Balsamic/coumarinic", 4, ""),
    "Cumin Oil":                 ("Spices", 2, ""),
    "Cyclogalbanate":            ("Herbal - Green", 1, ""),
    "Cypress Oil":               ("Woody - green", 1, ""),
    "Damascenone":               ("Fruits", 1, ""),
    "Damascone Alpha":           ("Fruits", 1, ""),
    "Damascone Beta":            ("Fruits", 1, ""),
    "DEP":                       ("Solvents", None, "solvent"),
    "Dewberry":                  ("Fruits", 1, "basis"),
    "Dihydromyrcenol":           ("Fresh", 0, ""),
    "Dimetol":                   ("Citrus", 0, ""),
    "Dynamone":                  ("Woody", 3, ""),
    "Ebanol":                    ("Woody - sandal", 4, ""),
    "Estragole":                 ("Spices", 0, ""),
    "Ethyl Acetoacetate":        ("Fruits", 0, ""),
    "Ethyl Linalool":            ("Flowers - green", 0, ""),
    "Ethyl Maltol":              ("Fruits", 3, "Veltol Plus"),
    "Ethyl Vanillin":            ("Balsamic/coumarinic", 4, ""),
    "Ethylene Brassylate":       ("Musks", 4, ""),
    "Eucalyptus Oil":            ("Fresh", 0, ""),
    "Eugenol":                   ("Spices", 3, ""),
    "Evernyl":                   ("Moss", 4, ""),
    "Exaltolide":                ("Musks", 4, ""),
    "Fir Balsam Absolute":       ("Woody - green", 3, ""),
    "Fixolide":                  ("Musks", 4, ""),
    "Floralozone":               ("Fresh", 1, ""),
    "Florol":                    ("Flowers - green", 2, ""),
    "Frankincense Resinoid":     ("Balsamic/coumarinic", 3, ""),
    "Galaxolide":                ("Musks", 4, ""),
    "Galbanum Oil":              ("Herbal - Green", 0, ""),
    "Galbex":                    ("Herbal - Green", 1, "galbanum-basis"),
    "Gamma Decalactone":         ("Fruits", 3, ""),
    "Geraniol":                  ("Flowers - red", 1, ""),
    "Geranium Egypt Oil":        ("Flowers - red", 1, ""),
    "Guaiacwood Oil":            ("Woody", 4, ""),
    "Habanolide":                ("Musks", 4, ""),
    "Hedione":                   ("Flowers - white", 2, ""),
    "Helional":                  ("Fresh", 1, ""),
    "Heliotropine":              ("Balsamic/coumarinic", 3, ""),
    "Hexalon":                   ("Fruits", 1, ""),
    "Hexyl Salicylate":          ("Flowers - spicy", 2, ""),
    "Hydroxycitronellal":        ("Flowers - green", 2, "'Hydroxy' in T. Girl hierheen gebracht"),
    "Indole":                    ("Animalic", 3, ""),
    "Ionone Beta":               ("Flowers - red", 3, ""),
    "Ionone Pure":               ("Flowers - red", 3, "alfa/beta-mengsel"),
    "Iso E Super":               ("Woody - amber", 4, ""),
    "Isoamyl Salicylate":        ("Flowers - spicy", 3, ""),
    "Isobornyl Acetate":         ("Woody - green", 0, ""),
    "Isobornyl Cyclohexanol":    ("Woody - sandal", 4, ""),
    "Isobutavan":                ("Balsamic/coumarinic", 4, "vanille-basis"),
    "Isobutyl Quinoline":        ("Earthy", 3, ""),
    "Isobutyl Salicylate":       ("Flowers - spicy", 2, ""),
    "Isodamascone":              ("Fruits", 1, ""),
    "Isoeugenol":                ("Spices", 4, ""),
    "Jacynth Body":              ("Flowers - green", 2, "hyacint-basis"),
    "Jasmin 231":                ("Flowers - white", 2, "basis"),
    "Jasmonal H":                ("Flowers - white", 3, "hexyl cinnamic aldehyde"),
    "Juniper Berry Oil":         ("Woody - green", 0, ""),
    "Kephalis":                  ("Amber", 3, "Cigalis hierheen gebracht"),
    "Labdanum Absolute":         ("Amber", 4, ""),
    "Lavandin Absolute":         ("Herbal - Green", 1, ""),
    "Lavandin Super Oil":        ("Herbal - Green", 0, ""),
    "Lavender Oil":              ("Herbal - Green", 0, ""),
    "Lemon Oil":                 ("Citrus", 0, "California-herkomst samengevoegd"),
    "Liffarome":                 ("Herbal - Green", 0, ""),
    "Lilial":                    ("Flowers - green", 3, ""),
    "Linalool":                  ("Flowers - green", 1, ""),
    "Linalool Oxide":            ("Flowers - green", 1, ""),
    "Linalyl Acetate":           ("Flowers - green", 1, ""),
    "Lyral":                     ("Flowers - green", 3, ""),
    "Mandarin Oil":              ("Citrus", 0, ""),
    "Mate Absolute":             ("Herbal - Green", 3, ""),
    "Mayol":                     ("Flowers - green", 2, ""),
    "Melisflor":                 ("Flowers - green", 2, "Firmenich-basis"),
    "Melonal":                   ("Fruits", 0, ""),
    "Menthol":                   ("Fresh", 0, ""),
    "Methyl Ionone Gamma":       ("Flowers - spicy", 3, ""),
    "Methyl Ionone Total":       ("Flowers - spicy", 3, ""),
    "Methyl Octine Carbonate":   ("Herbal - Green", 0, ""),
    "Mousse Metra":              ("Moss", 4, "eikenmos-vervanger"),
    "Musk Ambrette Substitute":  ("Musks", 4, ""),
    "Musk Ketone":               ("Musks", 4, ""),
    "Nerol":                     ("Flowers - red", 1, ""),
    "Neroli Substitute":         ("Bases & replacers", 0, ""),
    "Nutmeg Oil":                ("Spices", 0, ""),
    "Oakmoss Absolute":          ("Moss", 4, ""),
    "Orange Flower 1103":        ("Flowers - white", 1, "basis"),
    "Orange Oil":                ("Citrus", 0, ""),
    "Osyrol":                    ("Woody - sandal", 4, ""),
    "Patchouli Oil":             ("Woody", 4, ""),
    "Pepper Oil":                ("Spices", 0, ""),
    "Petitgrain Citronnier":     ("Citrus", 0, ""),
    "Phenyl Hexanol":            ("Flowers - green", 2, ""),
    "Phenylacetic Aldehyde":     ("Flowers - white", 1, ""),
    "Phenylethyl Alcohol":       ("Flowers - red", 2, ""),
    "Phenylethyl Phenylacetate": ("Flowers - red", 4, ""),
    "Phenylpropyl Alcohol":      ("Flowers - white", 2, ""),
    "Pomme Oliffac":             ("Fruits", 0, "appelbasis"),
    "Precyclemone B":            ("Flowers - green", 1, ""),
    "Reseda Acetal":             ("Flowers - green", 2, "in de bron 'Reseda Body'"),
    "Rose de Mai Absolute":      ("Flowers - red", 2, ""),
    "Rosemary Oil":              ("Herbal - Green", 0, ""),
    "Sandalore":                 ("Woody - sandal", 4, ""),
    "Sandalwood Firmenich":      ("Woody - sandal", 4, "basis, geen natuurlijke olie"),
    "Sandalwood Oil":            ("Woody - sandal", 4, ""),
    "Spearmint Oil":             ("Fresh", 0, ""),
    "Styrallyl Acetate":         ("Herbal - Green", 1, ""),
    "Tangerine Oil":             ("Citrus", 0, ""),
    "Tarragon Oil":              ("Herbal - Green", 0, "Estragon; mogelijk was estragole bedoeld"),
    "Terpineol":                 ("Flowers - green", 1, ""),
    "Terpinyl Acetate":          ("Herbal - Green", 1, ""),
    "Timberol":                  ("Woody", 4, ""),
    "Tonalid":                   ("Musks", 4, ""),
    "Traseolide":                ("Musks", 4, ""),
    "Triplal":                   ("Herbal - Green", 0, ""),
    "Undecavertol":              ("Flowers - green", 1, ""),
    "Vanillin":                  ("Balsamic/coumarinic", 4, ""),
    "Vertofix":                  ("Woody", 4, ""),
    "Vetiver Oil":               ("Woody", 4, ""),
    "Vetiver Java Oil":          ("Woody", 4, "andere olie dan Vetiver Ha\u00efti, zelfde CAS"),
    "Vetiveryl Acetate":         ("Woody", 4, ""),
    "Ylang Ylang Oil":           ("Flowers - white", 2, ""),
    # --- uit het nagekeken werkblad en de twee bases ---
    "Phenoxyacetaldehyde":       ("Fresh", 0, "in de bron 'Cortex Aldehyde'"),
    "Orris Givco":               ("Flowers - red", 3, "in de bron 'Irival'"),
    "Jasmin 1103 (Roure Bertrand base)": ("Flowers - white", 2, "basis"),
    "Oakmoss":                   ("Moss", 4, "in de bron 'Sylvester Oakmoss'"),
    "Scotch Pine":               ("Woody - green", 0, ""),
    "Althenol":                  ("Bases & replacers", 4, "eigen basis, formule in de app"),
    "Jasmin 231":                ("Flowers - white", 2, "eigen basis, formule in de app"),
    "Vetiverol":                 ("Woody", 4, ""),
    "Methyl Ionone":             ("Flowers - spicy", 3, "puur, niet gamma of total"),
    "Santalol":                  ("Woody - sandal", 4, ""),
    "Cinnamyl Acetate":          ("Balsamic/coumarinic", 3, ""),
    "Rose de Mai 68":            ("Flowers - red", 2, "apart van Rose de Mai Absolute"),
    "Jasmin Absolute Type":      ("Flowers - white", 2, "reconstructie, geen absolue"),
    "Peru Balsam":               ("Balsamic/coumarinic", 4, ""),
    "Ylang Extra":               ("Flowers - white", 2, "apart van Ylang Ylang Oil"),
    "Aurantiol":                 ("Flowers - white", 4, ""),
    "Benzyl Valerate":           ("Flowers - white", 2, ""),
    "Aldehyde C8":               ("Aldehydes", 0, ""),
    "Aldehyde C16":              ("Fruits", 3, "aardbei-lacton"),
    "Rhodinol":                  ("Flowers - red", 2, ""),
    "Benzyl Formate":            ("Flowers - white", 0, ""),
    "Ionone Alpha":              ("Flowers - red", 3, ""),
    "Para-Cresol":               ("Phenolic", 2, ""),
    "Rose de Mai 68":            ("Flowers - red", 2, "eigen basis, formule in de app"),
    "Geranyl Acetate":           ("Flowers - red", 1, ""),
    "Rhodinol Bourbon":          ("Flowers - red", 2, "apart gehouden van Rhodinol"),
    "Oeillet 35":                ("Flowers - spicy", 2, "eigen basis, formule in de app"),
    "Cinnamon Oil":              ("Spices", 2, "apart gehouden van Cinnamon Leaf Oil"),
    "Iris Butter":               ("Flowers - spicy", 3, ""),
    "Rose Orient Type":          ("Flowers - red", 2, "reconstructie"),
}

# CAS-nummers, enkel waar ze bevestigd zijn
CAS = {
    # uit de eigen materialenbibliotheek (exacte naamovereenkomst, 07/09/2026)
    "Adoxal":                              "141-13-9",
    "Aldehyde C12 MNA":                    "110-41-8",
    "Aldehyde C8":                         "124-13-0",
    "Allyl Amyl Glycolate":                "67634-00-8",
    "Ambrettolide":                        "7779-50-2",
    "Amyl Salicylate":                     "2050-08-0",
    "Aurantiol":                           "89-43-0",
    "Bacdanol":                            "28219-61-6",
    "Benzyl Acetate":                      "140-11-4",
    "Benzyl Salicylate":                   "118-58-1",
    "Bourgeonal":                          "18127-01-0",
    "Brahmanol":                           "72089-08-8",
    "Calone":                              "28940-11-6",
    "Canthoxal":                           "5462-06-6",
    "Cardamom Oil":                        "8000-66-6",
    "Cashmeran":                           "33704-61-9",
    "Cinnamon Leaf Oil":                   "8015-91-6",
    "Cinnamyl Acetate":                    "103-54-8",
    "Cis-3-Hexenol":                       "928-96-1",
    "Cis-3-Hexenyl Acetate":               "3681-71-8",
    "Cis-3-Hexenyl Salicylate":            "65405-77-8",
    "Citral":                              "5392-40-5",
    "Citronellol":                         "106-22-9",
    "Clary Sage Oil":                      "8016-63-5",
    "Coumarin":                            "91-64-5",
    "Damascenone":                         "23696-85-7",
    "Damascone Alpha":                     "24720-09-0",
    "Damascone Beta":                      "23726-91-2",
    "Dihydromyrcenol":                     "18479-58-8",
    "Dimetol":                             "13254-34-7",
    "Ebanol":                              "67801-20-1",
    "Ethyl Acetoacetate":                  "141-97-9",
    "Ethyl Linalool":                      "10339-55-6",
    "Ethyl Maltol":                        "4940-11-8",
    "Ethyl Vanillin":                      "121-32-4",
    "Ethylene Brassylate":                 "105-95-3",
    "Eugenol":                             "97-53-0",
    "Floralozone":                         "67634-15-5",
    "Florol":                              "63500-71-0",
    "Galaxolide":                          "1222-05-5",
    "Galbanum Oil":                        "8023-91-4",
    "Geraniol":                            "106-24-1",
    "Geranium Egypt Oil":                  "8000-46-2",
    "Geranyl Acetate":                     "105-87-3",
    "Guaiacwood Oil":                      "8016-23-7",
    "Habanolide":                          "111879-80-2",
    "Hedione":                             "24851-98-7",
    "Helional":                            "1205-17-0",
    "Hexalon":                             "79-78-7",
    "Hexyl Salicylate":                    "6259-76-3",
    "Hydroxycitronellal":                  "107-75-5",
    "Indole":                              "120-72-9",
    "Ionone Alpha":                        "127-41-3",
    "Iso E Super":                         "54464-57-2",
    "Isoamyl Salicylate":                  "87-20-7",
    "Isobornyl Acetate":                   "125-12-2",
    "Isobutavan":                          "20665-85-4",
    "Isobutyl Salicylate":                 "87-19-4",
    "Isoeugenol":                          "97-54-1",
    "Juniper Berry Oil":                   "84603-69-0",
    "Kephalis":                            "36306-87-3",
    "Labdanum Absolute":                   "8016-26-0",
    "Liffarome":                           "67633-96-9",
    "Lilial":                              "80-54-6",
    "Linalool":                            "78-70-6",
    "Linalyl Acetate":                     "115-95-7",
    "Lyral":                               "31906-04-4",
    "Mayol":                               "13828-37-0",
    "Melonal":                             "106-72-9",
    "Menthol":                             "2216-51-5",
    "Methyl Octine Carbonate":             "111-80-8",
    "Musk Ketone":                         "81-14-1",
    "Nerol":                               "106-25-2",
    "Nutmeg Oil":                          "8008-45-5",
    "Oakmoss":                             "9000-50-4",
    "Oakmoss Absolute":                    "9000-50-4",
    "Osyrol":                              "41890-92-0",
    "Para-Cresol":                         "106-44-5",
    "Patchouli Oil":                       "8014-09-3",
    "Peru Balsam":                         "8007-00-9",
    "Precyclemone B":                      "52474-60-9",
    "Sandalore":                           "65113-99-7",
    "Spearmint Oil":                       "8008-79-5",
    "Styrallyl Acetate":                   "93-92-5",
    "Terpinyl Acetate":                    "80-26-2",
    "Tonalid":                             "1506-02-1",
    "Triplal":                             "68039-49-6",
    "Undecavertol":                        "81782-77-6",
    "Vanillin":                            "121-33-5",
    "Vetiver Oil":                         "8016-96-4",
    "Vetiverol":                           "89-88-3",
    "Ylang Ylang Oil":                     "8006-81-3",
    # handmatig bevestigd
    "Reseda Acetal": "67633-94-7",
}

# IFRA-limiet voor Category 4, in %. Codering van de app: 99 = gecontroleerd,
# geen beperking; leeg = nog niet ingegeven. Bron per materiaal:
#   "std NNN"  = IFRA Standards Library, standaard NNN, Category 4
#   "eigen"    = overgenomen uit de eigen materialenbibliotheek (natuurlijke
#                oliën zonder eigen standaard, met een afgeleide limiet)
#   "geen std" = het CAS-nummer komt niet voor in de Standards Library
IFRA = {
    "Adoxal":                          99,       # geen std
    "Aldehyde C12 MNA":                99,       # geen std
    "Aldehyde C8":                     99,       # geen std
    "Allyl Amyl Glycolate":            99,       # geen std
    "Ambrettolide":                    99,       # geen std
    "Amyl Salicylate":                 99,       # geen std
    "Aurantiol":                       99,       # geen std
    "Bacdanol":                        99,       # geen std
    "Benzyl Acetate":                  99,       # geen std
    "Benzyl Salicylate":               7.3,      # std 011
    "Bourgeonal":                      0.47,     # std 014
    "Brahmanol":                       99,       # geen std
    "Calone":                          99,       # geen std
    "Canthoxal":                       2.5,      # std 057
    "Cardamom Oil":                    99,       # geen std
    "Cashmeran":                       3.8,      # std 028
    "Cinnamon Leaf Oil":               3.24,     # eigen
    "Cinnamyl Acetate":                99,       # geen std
    "Cis-3-Hexenol":                   99,       # geen std
    "Cis-3-Hexenyl Acetate":           99,       # geen std
    "Cis-3-Hexenyl Salicylate":        99,       # geen std
    "Citral":                          0.6,      # std 021
    "Citronellol":                     12,       # std 022
    "Clary Sage Oil":                  99,       # geen std
    "Coumarin":                        1.5,      # std 023
    "Damascenone":                     0.043,    # std 077
    "Damascone Alpha":                 0.043,    # std 077
    "Damascone Beta":                  0.043,    # std 077
    "Dihydromyrcenol":                 99,       # geen std
    "Dimetol":                         99,       # geen std
    "Ebanol":                          99,       # geen std
    "Ethyl Acetoacetate":              99,       # geen std
    "Ethyl Linalool":                  99,       # geen std
    "Ethyl Maltol":                    99,       # geen std
    "Ethyl Vanillin":                  99,       # geen std
    "Ethylene Brassylate":             99,       # geen std
    "Eugenol":                         2.5,      # std 035
    "Floralozone":                     99,       # geen std
    "Florol":                          99,       # geen std
    "Galaxolide":                      99,       # geen std
    "Galbanum Oil":                    99,       # geen std
    "Geraniol":                        4.7,      # std 037
    "Geranium Egypt Oil":              26.5,     # eigen
    "Geranyl Acetate":                 99,       # geen std
    "Guaiacwood Oil":                  99,       # geen std
    "Habanolide":                      99,       # geen std
    "Hedione":                         99,       # geen std
    "Helional":                        2.6,      # std 059
    "Hexalon":                         99,       # geen std
    "Hexyl Salicylate":                6.5,      # std 042
    "Hydroxycitronellal":              2.1,      # std 043
    "Indole":                          99,       # geen std
    "Ionone Alpha":                    99,       # geen std
    "Iso E Super":                     20,       # std 068
    "Isoamyl Salicylate":              99,       # geen std
    "Isobornyl Acetate":               99,       # geen std
    "Isobutavan":                      99,       # geen std
    "Isobutyl Salicylate":             99,       # geen std
    "Isoeugenol":                      0.11,     # std 048
    "Juniper Berry Oil":               99,       # geen std
    "Kephalis":                        99,       # geen std
    "Labdanum Absolute":               27.78,    # eigen
    "Liffarome":                       0.56,     # std 246
    "Lilial":                          1.4,      # std 015
    "Linalool":                        99,       # std 187 specification
    "Linalyl Acetate":                 99,       # geen std
    "Lyral":                           0.2,      # std 044
    "Mayol":                           4.7,      # std 208
    "Melonal":                         99,       # geen std
    "Menthol":                         99,       # geen std
    "Methyl Octine Carbonate":         0.01,     # std 064
    "Musk Ketone":                     99,       # std 189 specification
    "Nerol":                           99,       # geen std
    "Nutmeg Oil":                      99,       # geen std
    "Oakmoss":                         0.1,      # std 067
    "Oakmoss Absolute":                0.1,      # std 067
    "Osyrol":                          99,       # geen std
    "Para-Cresol":                     0.005,    # std 260
    "Patchouli Oil":                   99,       # geen std
    "Peru Balsam":                     0.41,     # std 071
    "Precyclemone B":                  99,       # geen std
    "Reseda Acetal":                   99,       # geen std
    "Sandalore":                       1.2,      # std 212
    "Spearmint Oil":                   0.65,     # eigen
    "Styrallyl Acetate":               99,       # geen std
    "Terpinyl Acetate":                99,       # geen std
    "Tonalid":                         99,       # geen std
    "Triplal":                         2.5,      # std 030
    "Undecavertol":                    99,       # geen std
    "Vanillin":                        99,       # geen std
    "Vetiver Oil":                     99,       # geen std
    "Vetiverol":                       99,       # geen std
    "Ylang Ylang Oil":                 0.73,     # std 084
}

# Hernoemingen uit het nagekeken werkblad: de naam zoals Mathieu die in zijn
# eigen bibliotheek voert. Wordt toegepast na MAP, dus INFO en IFRA blijven op
# de oude sleutel staan.
HERNOEM = {
    "Aldehyde C14": "Aldehyde C14 peach",
    "Aldehyde C16": "Aldehyde C16 strawberry",
    "Anisic Aldehyde": "Anisaldehyde",
    "Basil Oil": "Basil sweet EO",
    "Benzoin Resinoid": "Benzoin Sumatra res. (Firm.)",
    "Carrot Seed Oil": "Carrot seed India",
    "Celery Oil": "Celery seed EO",
    "Cinnamic Alcohol": "Cinnamyl alcohol",
    "Cinnamon Oil": "Cinnamon leaf EO",
    "Cis-Jasmone": "Jasmone cis",
    "Clove Oil": "Clove buds EO",
    "Coriander Oil": "Coriander seed EO",
    "Cumin Oil": "Cumin seed EO",
    "Cypress Oil": "Cypress EO (IFF)",          # "-NOFro" is een eigen vriezernotitie, weggelaten
    "Fir Balsam Absolute": "Fir balsam abs.",   # "in ?" weggelaten, oplosmiddel onbekend
    "Gamma Decalactone": "Decalactone gamma",
    "Lavandin Super Oil": "Lavandin grosso EO",
    "Linalool Oxide": "Linalool oxide furanoid",
    "Mandarin Oil": "Mandarin yellow It. EO",
    "Orange Oil": "Orange sweet CP EO",
    "Phenyl Hexanol": "Mefranal",
    "Phenylethyl Alcohol": "Phenyl Ethyl Alcohol (PEA)",
    "Rosemary Oil": "Rosemary CT camphor EO",
    "Sandalwood Oil": "Sandalwood India EO",
    "Vertofix": "Vertofix c\u0153ur",
    "Vetiveryl Acetate": "Vetiveryl acetate Haiti",
    "Ylang Extra": "Ylang ylang extra",
}

# CAS uit het nagekeken werkblad
CAS.update({
    "Benzyl Valerate": "10361-39-4",
    "Ionone Beta": "14901-07-6",        # in het werkblad stond 14901-07-06, een cijfer te veel
    "Iris Butter": "8002-73-1",
    "Isobutyl Quinoline": "93-19-6",
    "Isodamascone": "39872-57-6",
    "Jasmonal H": "101-86-0",
    "Lavandin Absolute": "8022-15-9",
    "Lavandin Super Oil": "8022-18-2",
})

# IFRA voor de CAS-nummers uit het nagekeken werkblad
IFRA.update({
    "Benzyl Valerate": 99,       # geen std
    "Ionone Beta": 99,           # geen std
    "Iris Butter": 99,           # geen std
    "Isobutyl Quinoline": 99,    # geen std
    "Isodamascone": 0.043,       # std 077, rose ketones
    "Jasmonal H": 9.9,           # std 040
    "Lavandin Absolute": 99,     # geen std
    "Lavandin Super Oil": 99,    # geen std
})

# CAS uit de eigen bibliotheek, tweede ronde na de hernoemingen
CAS.update({
    "Aldehyde C14 peach":                "104-67-6",
    "Aldehyde C16 strawberry":           "77-83-8",
    "Anisaldehyde":                      "123-11-5",
    "Basil sweet EO":                    "84775-71-3",
    "Benzoin Sumatra res. (Firm.)":      "9000-05-9",
    "Carrot seed India":                 "8015-88-1",
    "Celery seed EO":                    "8015-90-5",
    "Cinnamon leaf EO":                  "8015-91-6",
    "Cinnamyl alcohol":                  "104-54-1",
    "Clove buds EO":                     "8000-34-8",
    "Coriander seed EO":                 "8008-52-4",
    "Cumin seed EO":                     "8014-13-9",
    "Decalactone gamma":                 "706-14-9",
    "Jasmone cis":                       "488-10-8",
    "Linalool oxide furanoid":           "60047-17-8",
    "Mandarin yellow It. EO":            "8008-31-9",
    "Mefranal":                          "55066-49-4",
    "Phenyl Ethyl Alcohol (PEA)":        "60-12-8",
    "Rosemary CT camphor EO":            "8000-25-7",
    "Vertofix cœur":                     "32388-55-9",
    "Vetiver Haïti (AV)":                "8016-96-4",
    "Vetiveryl acetate Haiti":           "62563-80-8",
    "Ylang ylang extra":                 "8006-81-3",
})

# IFRA, tweede ronde
IFRA.update({
    "Aldehyde C14 peach":                99,       # geen std
    "Aldehyde C16 strawberry":           99,       # geen std
    "Anisaldehyde":                      1.4,      # std 054
    "Basil sweet EO":                    99,       # geen std
    "Benzoin Sumatra res. (Firm.)":      6,        # eigen
    "Carrot seed India":                 99,       # geen std
    "Celery seed EO":                    99,       # geen std
    "Cinnamon leaf EO":                  3.24,     # eigen
    "Cinnamyl alcohol":                  1.2,      # eigen
    "Clove buds EO":                     99,       # geen std
    "Coriander seed EO":                 99,       # geen std
    "Cumin seed EO":                     0.4,      # eigen
    "Decalactone gamma":                 99,       # geen std
    "Jasmone cis":                       99,       # geen std
    "Linalool oxide furanoid":           99,       # geen std
    "Mandarin yellow It. EO":            99,       # geen std
    "Mefranal":                          99,       # geen std
    "Phenyl Ethyl Alcohol (PEA)":        99,       # geen std
    "Rosemary CT camphor EO":            99,       # geen std
    "Vertofix cœur":                     99,       # geen std
    "Vetiver Haïti (AV)":                99,       # geen std
    "Vetiveryl acetate Haiti":           0.9,      # eigen
    "Ylang ylang extra":                 0.73,     # eigen
})

# vier materialen waarvan ik de eigen annotatie uit de naam haalde, met hun
# CAS en IFRA rechtstreeks uit de bibliotheekregel, plus Rhodinol
CAS.update({
    "Cypress EO (IFF)": "8013-86-3",
    "Fir balsam abs.": "8007-47-4",
    "Orange sweet CP EO": "8028-48-6",
    "Sandalwood India EO": "8006-87-9",
    "Rhodinol": "141-25-3",
})
IFRA.update({
    "Cypress EO (IFF)": 99,        # eigen bibliotheek
    "Fir balsam abs.": 99,         # eigen bibliotheek
    "Orange sweet CP EO": 99,      # geen std, citrusolie zonder eigen limiet
    "Sandalwood India EO": 99,     # eigen bibliotheek
    "Rhodinol": 12,                # eigen bibliotheek, gelijk aan citronellol
})

# Vetiver Java en Vetiver Haiti zijn verschillende olien met hetzelfde CAS
CAS["Vetiver Java Oil"] = "8016-96-4"
IFRA["Vetiver Java Oil"] = 99          # geen std
