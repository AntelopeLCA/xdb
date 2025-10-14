import dash_bootstrap_components as dbc
from dash import html


def landing_text():
    return dbc.Row([
        dbc.Col([
            html.P(["""Welcome to """,
                    html.Strong("qdb"), """, 
    the Antelope quantity database!  This is a database of flowables, contexts, and quantities, and
    the characterization factors that relate them.  Use it to look up flow properties, compare LCIA
    methods, and benchmark your own results.
            """]),
            html.P(["""
    Search for any term. Results for flowables, contexts, and quantities will show up separately. If you click 
    the info button for a search result, you will be shown details about that term. All terms have synonyms, 
    plus contexts have a hierarchical organization, and quantities (like LCIA methods) have documentary 
    information."""]),
            html.P(["""Add flowables 
    and quantities from the search results to your selection to perform an analysis (retrieve the 
    characterization factors that relate those flowables to those quantities). The results can be filtered by
    contexts. Results can be exported to CSV, Excel, and JSON on the Analyze page."""], className='text-justify')
            ], width=8),
        html.H3('QDB Search', className='text-center'),
    ], justify="center")
