"""
Detail Page Component

Displays detailed information about a selected entity (flowable, context, or quantity).
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


# STUB: Replace with actual backend retrieval
def get_entity_details(entity_type, entity_id):
    """
    STUB: Retrieve detailed information about an entity from the backend.

    Args:
        entity_type: Type of entity ('flowable', 'context', 'quantity')
        entity_id: ID of the entity

    Returns:
        Dictionary with entity details, or None if not found
    """
    # TODO: Implement actual backend retrieval
    # This should call into your backend resources
    return None


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

    # Get entity details (STUB call)
    details = get_entity_details(entity_type, entity_id)

    if not details:
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

    # Build the detail view
    return html.Div([
        # Header with back button
        dbc.Row([
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
                html.H3(f'{entity_type.capitalize()}: {details.get("name", entity_id)}',
                       className='mb-3')
            ])
        ]),

        # Entity details section
        dbc.Card([
            dbc.CardHeader(html.H5('Details')),
            dbc.CardBody([
                html.Div(id='entity-details-content', children=[
                    # STUB: This would be populated with actual entity data
                    _create_detail_fields(details)
                ])
            ])
        ], className='mb-3'),

        # Related information section (optional)
        dbc.Card([
            dbc.CardHeader(html.H5('Related Information')),
            dbc.CardBody([
                html.Div(id='entity-related-content', children=[
                    html.P('Related information will be displayed here.',
                           className='text-muted', style={'fontStyle': 'italic'})
                ])
            ])
        ])
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
