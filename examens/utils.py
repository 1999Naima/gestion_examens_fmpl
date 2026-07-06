# examens/utils.py
"""
Utilitaires pour la répartition des étudiants dans les amphithéâtres.
"""

SIEGES_PAR_TABLE = 10
SIEGES_PAR_COTE = 5  # 5 à gauche + 5 à droite par table


def decode_seat_position(numero_siege, sieges_par_table=SIEGES_PAR_TABLE,
                         sieges_par_cote=SIEGES_PAR_COTE, total_tables=15):
    """
    Décode un numéro de siège continu (1 → N) en position physique
    dans l'amphithéâtre : numéro de table, côté (gauche/droite),
    et position dans le groupe de 5.

    Numérotation : la table 1 contient les sièges 1-10,
    la table 2 contient 11-20, etc.
    Dans chaque table : positions 1-5 = côté gauche (de gauche à droite),
    positions 6-10 = côté droit (de gauche à droite).

    Retourne un dict :
        {
            'table': int,            # numéro de la table (1-indexed)
            'cote': 'gauche'|'droite',
            'position_cote': int,    # position 1-5 dans le groupe
            'position_table': int,   # position 1-10 dans la table
            'label': str,            # ex: "2ème table à gauche, place 4"
            'row_percent': float,    # 0-100 : position verticale pour diagramme SVG
        }
    """
    if numero_siege is None or numero_siege < 1:
        return None

    index = numero_siege - 1  # 0-indexed
    table_num = (index // sieges_par_table) + 1
    position_table = (index % sieges_par_table) + 1  # 1 → 10

    if position_table <= sieges_par_cote:
        cote = 'gauche'
        position_cote = position_table
    else:
        cote = 'droite'
        position_cote = position_table - sieges_par_cote

    label = _build_label(table_num, cote, position_cote)

    # Position verticale en % (0 = devant/tableau, 100 = fond de salle)
    row_percent = round(((table_num - 1) / max(total_tables - 1, 1)) * 100, 1)

    # Coordonnée Y en pixels pour le marqueur SVG (zone salle : y=28 à y=146)
    svg_y_top, svg_y_bottom = 38, 136  # marge de 10px en haut/bas du bloc salle
    svg_cy = round(svg_y_top + (row_percent / 100) * (svg_y_bottom - svg_y_top), 1)
    svg_cy_text = round(svg_cy + 3, 1)  # léger décalage pour centrer le texte verticalement

    return {
        'table': table_num,
        'cote': cote,
        'position_cote': position_cote,
        'position_table': position_table,
        'label': label,
        'row_percent': row_percent,
        'svg_cy': svg_cy,
        'svg_cy_text': svg_cy_text,
    }


def _ordinal_fr(n):
    """Renvoie l'ordinal français : 1 → '1ère', 2 → '2ème', etc."""
    if n == 1:
        return "1ère"
    return f"{n}ème"


def _build_label(table_num, cote, position_cote):
    """Construit le texte indicatif, ex: '2ème table à gauche, place 4'."""
    table_ord = _ordinal_fr(table_num)
    return f"{table_ord} table à {cote}, place {position_cote}"
