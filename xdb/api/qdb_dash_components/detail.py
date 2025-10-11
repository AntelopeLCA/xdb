"""
Detail Page Component

Displays detailed information about a selected entity (flowable, context, or quantity).
"""

from dash import html, dcc
import dash_bootstrap_components as dbc

from ..runtime import cat

import urllib.parse


def get_flowable(entity_id):
    """
    STUB: Retrieve detailed information about an entity from the backend.

    Args:
        entity_id: ID of the entity

    Returns:
        Dictionary with entity details, or None if not found
    """
    return cat.lcia_engine.get_flowable(entity_id)


def get_context(context_name):
    return cat.lcia_engine[context_name]


def get_quantity(quantity_uuid):
    return cat.lcia_engine.get_canonical(quantity_uuid)


# STUB: Replace with actual backend retrieval
def get_entity_details(entity_type, entity_id):
    if entity_type == 'flowable':
        return get_flowable(entity_id)
    elif entity_type == 'quantity':
        return get_quantity(entity_id)
    elif entity_type == 'context':
        return get_context(entity_id)
    return None


def _header(entity_type, entity_name):
    return dbc.Row([
            dbc.Col([
                dbc.Button(
                    html.I(className='bi bi-arrow-left'),
                    href='/qdb.dash/',
                    color='secondary',
                    size='sm',
                    className='mb-3'
                )
            ], width='auto'),
            dbc.Col([
                html.H3(f'{entity_type.capitalize()}: {entity_name}',
                        className='mb-3')
            ])
        ])


def _add_button(entity_type, entity_id):
    """
    Create an add/remove button that will be dynamically updated by callback.

    :param entity_type:
    :param entity_id:
    :return:
    """
    return html.Div([
        dbc.Button(
            'Add to Selection',  # Default text, will be updated by callback
            id={'type': 'detail-add-button', 'index': f'{entity_type}:{entity_id}'},
            color='success',  # Default color, will be updated by callback
            className='text-center'
        )
    ], className='text-center')


def _flowable_term(term):
    """

    :param term:
    :return:
    """
    return html.P(term, style={"margin-bottom": 0})


def flowable_view(flowable):
    # Build the detail view
    return html.Div([
        # Header with back button
        _header('flowable', flowable.name),
        dbc.Row([
            dbc.Col([], width=3),
            dbc.Col([
                # Entity details section
                dbc.Card([
                    dbc.CardHeader(html.H5('Synonyms')),
                    dbc.CardBody([
                        html.Div(id='entity-details-content', children=list(
                            _flowable_term(t) for t in sorted(flowable.terms) if t != flowable.name
                        ))
                        ])
                ]),
                _add_button('flowable', flowable.name)
            ], width=6),
            dbc.Col([], width=3)
        ], className='mb-3')
        ])


def _cx_parent(cx):
    if cx.parent:
        return html.A(dbc.Card([
            dbc.CardHeader(html.H5('Parent')),
            dbc.CardBody([cx.parent.name]),
            ]),
            href='/qdb.dash/detail/context/%s' % cx.parent.name)


def _cx_sense(cx):
    if cx.sense:
        return dbc.Card([
            dbc.CardHeader(html.H5(cx.sense),
                           className='bg-success' if cx.sense == 'Source' else 'bg-warning'),
            ])


def _cx_sub(sub):
    return html.A(dbc.Card([
        dbc.CardHeader(html.H5(sub.name)),
        ]),
        href='/qdb.dash/detail/context/%s' % sub)


def context_view(context):
    # Build the detail view
    return html.Div([
        # Header with back button
        _header('context', ' > '.join(context.as_list())),
        dbc.Row([
            dbc.Col([_cx_parent(context)
                    ]),
            dbc.Col([
                # Entity details section
                _cx_sense(context),
                dbc.Card([
                    dbc.CardHeader(html.H5('Synonyms')),
                    dbc.CardBody([
                        html.Div(id='entity-details-content', children=list(
                            _flowable_term(t) for t in sorted(context.terms) if t != context.name
                        ))
                        ])
                ]),
                _add_button('context', context.name)
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5('Subcompartments')),
                    dbc.CardBody([
                        html.Div(id='entity-details-content', children=list(
                            _cx_sub(t) for t in sorted(context.subcompartments, key=lambda x: x.name)
                        ))
                    ])

                ])
            ], width=4)
        ], className='mb-3')
    ])


def _q_prop(prop, value):
    return dbc.Row([
            dbc.Col(html.Strong(f'{prop}:'), width=3),
            dbc.Col(html.Span(str(value)), width=5)
        ], className='mb-2')


def quantity_view(quantity):
    # Build the detail view
    return html.Div([
        # Header with back button
        _header('quantity', quantity.name),
        dbc.Row([
            dbc.Col([], width=2),
            dbc.Col([
                # Entity details section
                dbc.Card([
                    dbc.CardHeader(html.H5('Properties')),
                    dbc.CardBody([
                        html.Div(id='entity-details-content', children=list(
                            _q_prop(prop, quantity[prop]) for prop in quantity.properties()))
                        ])
                    ]),
                dbc.Card([
                    dbc.CardHeader(html.H5('Synonyms')),
                    dbc.CardBody([
                        html.Div(id='entity-details-content', children=list(
                            _flowable_term(t) for t in sorted(cat.synonyms(quantity.uuid)) if t != quantity.name
                        ))
                        ])
                ]),
                _add_button('quantity', quantity.uuid)
            ], width=8),
            dbc.Col([], width=2)
        ], className='mb-3')
        ])


def create_detail_page(entity_type=None, entity_id=None):
    """
    Create the detail page for viewing entity information.

    Args:
        entity_type: Type of entity to display
        entity_id: ID of the entity to display

    Returns:
        A Dash component containing the detail view
    """
    if not entity_type or not entity_id:
        return html.Div([
            dbc.Alert(
                'No entity specified. Please select an item to view.',
                color='warning'
            ),
            dbc.Button(
                'Back to Search',
                href='/qdb.dash/',
                color='primary'
            )
        ])

    entity_id = urllib.parse.unquote(entity_id)

    # Get entity details (STUB call)
    entity = get_entity_details(entity_type, entity_id)

    if entity:
        if entity_type == 'flowable':
            return flowable_view(entity)
        elif entity_type == 'quantity':
            return quantity_view(entity)
        elif entity_type =='context':
            return context_view(entity)
    return html.Div([
        dbc.Alert(
            f'Entity not found: {entity_type} with ID {entity_id}',
            color='danger'
        ),
        dbc.Button(
            'Back to Search',
            href='/qdb.dash/',
            color='primary'
        )
    ])


def _create_detail_fields(details):
    """
    Create a formatted display of entity detail fields.

    Args:
        details: Dictionary of entity details

    Returns:
        Dash components displaying the fields
    """
    if not details:
        return html.P('No details available.', className='text-muted')

    fields = []
    for key, value in details.items():
        if key == 'name':
            continue  # Already shown in header

        fields.append(
            dbc.Row([
                dbc.Col(html.Strong(f'{key.replace("_", " ").title()}:'), width=3),
                dbc.Col(html.Span(str(value)), width=9)
            ], className='mb-2')
        )

    return fields if fields else html.P('No additional details available.',
                                        className='text-muted')
