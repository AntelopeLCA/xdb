"""
Landing Page Callbacks

Callbacks for search functionality and result interactions.
"""

from dash import Input, Output, State, html, ALL, ctx, no_update
import dash_bootstrap_components as dbc
from .landing import create_result_item
from ..runtime import cat

import logging


# STUB: Replace with actual backend search implementation
def search_backend(query, entity_type):
    """
    STUB: Search the backend for entities matching the query.

    Args:
        query: Search string
        entity_type: Type of entity to search ('flowable', 'context', 'quantity')

    Returns:
        List of dicts with 'id' and 'name' keys
    """
    # TODO: Implement actual backend search
    # This should call into your backend resources
    return []


def register(app):
    """Register landing page callbacks."""

    @app.callback(
        Output('search-results-cache', 'data'),
        Input('search-button', 'n_clicks'),
        Input('search-input', 'n_submit'),  # NEW: Trigger on Enter key
        State('search-input', 'value'),
        State('search-results-cache', 'data'),
        prevent_initial_call=True
    )
    def perform_search(n_clicks, n_submit, search_query, existing_results):
        """
        Execute search and store raw results.

        Args:
            n_clicks: Number of times search button was clicked
            search_query: The search string

        Returns:
            Dictionary with raw search results
        """

        logging.warning('entering perform_search with %s (existing %s)' % (search_query, existing_results.get('queries')))
        if (not n_clicks or n_clicks == 0) and (not n_submit or n_submit == 0):
            logging.warning('n_clicks is None or 0, using no_update')
            return no_update

        if not search_query or not search_query.strip():
            logging.warning('returning empty')
            return {'flowables': [], 'contexts': [], 'quantities': [], 'queries': []}

        lquery = search_query.strip().lower()

        if len(existing_results.get('queries', [])) > 0:
            """ narrow the search """
            flowables = list(cat.lcia_engine.get_flowable(k['id']) for k in existing_results['flowables']
                             if k['id'].lower().find(lquery) >= 0)
            contexts = list(cat.lcia_engine[k['id']] for k in existing_results['contexts']
                            if k['id'].lower().find(lquery) >= 0)
            quantities = list(cat.lcia_engine.get_canonical(k['id']) for k in existing_results['quantities']
                              if k['name'].lower().find(lquery)>= 0)
            queries = existing_results['queries'] + [search_query]

        else:
            # Search each entity type
            flowables = list(cat.lcia_engine.flowables(search=search_query))
            contexts = list(cat.lcia_engine.contexts(search=search_query))
            quantities = list(cat.lcia_engine.quantities(search=search_query))
            if len(flowables) + len(contexts) + len(quantities) == 0:
                queries = []
            else:
                queries = [search_query]

        # Store as serializable data
        return {
            'flowables': [
                {'id': item.name, 'name': '%s (%d terms)' % (item.name, len(item))}
                for item in flowables
            ],
            'contexts': [
                {'id': item.fullname, 'name': item.name}
                for item in contexts
            ],
            'quantities': [
                {'id': item.uuid, 'name': item['name']}
                for item in quantities
            ],
            'queries': queries
        }

    @app.callback(
        Output('flowables-results', 'children'),
        Output('contexts-results', 'children'),
        Output('quantities-results', 'children'),
        Output('current-search-queries', 'children'),
        Output('clear-search-button', 'color'),
        Output('search-button', 'value'),
        Input('search-results-cache', 'data'),
        Input('user-selection', 'data'),
    )
    def render_search_results(search_results, selection_data):
        """
        Render search results with current selection state.
        This callback fires both when search results change AND when selection changes.

        Args:
            search_results: Raw search results from cache
            selection_data: Current user selection

        Returns:
            Tuple of (flowables_results, contexts_results, quantities_results)
        """
        # logging.warning('render sr %s' % pathname)
        '''
        if pathname and (pathname.startswith('/qdb.dash/detail') or
            pathname.endswith('/analyze') or
            pathname.endswith('/debug')):
            return no_update, no_update, no_update
        '''
        if not search_results:
            empty_msg = html.P('No results yet. Enter a search term above.',
                             className='text-muted', style={'fontStyle': 'italic'})
            return empty_msg, empty_msg, empty_msg, None, 'secondary', 'Search'

        # Get current selections for each type
        selected_flowables = set(selection_data.get('flowables', []))
        selected_contexts = set(selection_data.get('contexts', []))
        selected_quantities = set(selection_data.get('quantities', []))

        nada = True

        # Render flowables
        flowables = search_results.get('flowables', [])
        if flowables:
            nada = False
            flowables_results = [html.P(["%d" % len(flowables), "items"])] + [create_result_item(
                    item['id'],
                    item['name'],
                    'flowable',
                    is_selected=(item['id'] in selected_flowables)
                )
                for item in flowables
            ]
        else:
            flowables_results = html.P('No flowables found.',
                                      className='text-muted', style={'fontStyle': 'italic'})

        # Render contexts
        contexts = search_results.get('contexts', [])
        if contexts:
            nada = False
            contexts_results = [html.P(["%d" % len(contexts), "items"])] + [create_result_item(
                    item['id'],
                    item['name'],
                    'context',
                    is_selected=(item['id'] in selected_contexts)
                )
                for item in contexts
            ]
        else:
            contexts_results = html.P('No contexts found.',
                                     className='text-muted', style={'fontStyle': 'italic'})

        # Render quantities
        quantities = search_results.get('quantities', [])
        if quantities:
            nada = False
            quantities_results = [html.P(["%d" % len(quantities), "items"])] + [create_result_item(
                    item['id'],
                    item['name'],
                    'quantity',
                    is_selected=(item['id'] in selected_quantities)
                )
                for item in quantities
            ]
        else:
            quantities_results = html.P('No quantities found.',
                                       className='text-muted', style={'fontStyle': 'italic'})

        if nada:
            sq_msg = 'No Results!'
            sb_msg = 'Search'
        else:
            sq_msg = 'Search Queries '
            sb_msg = 'Refine'
        q_entries = [dbc.ListGroupItem(sq_msg,
                                       style={'fontWeight': 'bold', 'border': 'none'})]

        for q in search_results.get('queries', []):
            q_entries.append(dbc.ListGroupItem(q))
        current_queries = dbc.ListGroup(q_entries, horizontal=True)

        return flowables_results, contexts_results, quantities_results, current_queries, 'primary', sb_msg


    @app.callback(
        Output('user-selection', 'data', allow_duplicate=True),
        Input({'type': 'add-button', 'index': ALL}, 'n_clicks'),
        State('user-selection', 'data'),
        prevent_initial_call=True
    )
    def add_to_selection(n_clicks_list, selection_data):
        """
        Add an item to the user's selection.

        Args:
            n_clicks_list: List of click counts for all add buttons
            selection_data: Current user selection

        Returns:
            Updated selection data
        """
        if not ctx.triggered_id:
            return selection_data

        # NEW: Check if this was an actual click (not just initialization)
        triggered_value = ctx.triggered[0]['value']

        # If n_clicks is None or 0, it's just initialization, not a real click
        if triggered_value is None or triggered_value == 0:
            return selection_data

        # Get the clicked button's index (format: "type:id")
        button_index = ctx.triggered_id['index']
        entity_type, entity_id = button_index.split(':', 1)

        logging.warning('add_to_selection %s' % button_index)
        new_selection = {
            'flowables': selection_data.get('flowables', []).copy(),
            'contexts': selection_data.get('contexts', []).copy(),
            'quantities': selection_data.get('quantities', []).copy()
        }

        # Add to appropriate list
        if entity_type == 'flowable':
            if entity_id in selection_data['flowables']:
                logging.warning('aa fx')
                new_selection['flowables'].remove(entity_id)
            else:
                logging.warning('aa fp')
                new_selection['flowables'].append(entity_id)
        elif entity_type == 'context':
            if entity_id in selection_data['contexts']:
                logging.warning('aa cx')
                new_selection['contexts'].remove(entity_id)
            else:
                logging.warning('aa cp')
                new_selection['contexts'].append(entity_id)
        elif entity_type == 'quantity':
            if entity_id in selection_data['quantities']:
                logging.warning('aa qx')
                new_selection['quantities'].remove(entity_id)
            else:
                logging.warning('aa qp')
                new_selection['quantities'].append(entity_id)
        else:
            logging.error('aa 00')

        return new_selection

    @app.callback(
        Output('search-results-cache', 'data', allow_duplicate=True),
        Input({'type': 'remove-button', 'index': ALL}, 'n_clicks'),
        State('search-results-cache', 'data'),
        prevent_initial_call=True
    )
    def remove_from_results(n_clicks_list, search_results):
        """
        Remove an item from the search results cache.

        Args:
            n_clicks_list: List of click counts for all remove buttons
            search_results: Current search results cache

        Returns:
            Updated search results cache
        """
        if not ctx.triggered_id:
            logging.warning('No ctx.triggered_id')
            return search_results

        # Check if this was an actual click (not just initialization)
        triggered_value = ctx.triggered[0]['value']
        if triggered_value is None or triggered_value == 0:
            return search_results

        # Get the clicked button's index (format: "type:id")
        button_index = ctx.triggered_id['index']
        entity_type, entity_id = button_index.split(':', 1)
        logging.warning('remove_from_results %s entity_type %s entity_id %s' % (button_index, entity_type, entity_id))

        # Remove from appropriate list in cache
        if entity_type == 'flowable':
            search_results['flowables'] = [
                item for item in search_results.get('flowables', [])
                if item['id'] != entity_id
            ]
        elif entity_type == 'context':
            search_results['contexts'] = [
                item for item in search_results.get('contexts', [])
                if item['id'] != entity_id
            ]
        elif entity_type == 'quantity':
            search_results['quantities'] = [
                item for item in search_results.get('quantities', [])
                if item['id'] != entity_id
            ]

        return search_results

    @app.callback(
        Output('search-results-cache', 'data', allow_duplicate=True),
        # Output('clear-search-button', 'color'),
        Output('search-input', 'value', allow_duplicate=True),
        Input('clear-search-button', 'n_clicks'),
        prevent_initial_call=True
        )
    def clear_search(n_clicks):
        """Clear the search cache."""
        if not n_clicks or n_clicks == 0:
            return no_update

        logging.warning('Clearing search cache')
        return {'flowables': [], 'contexts': [], 'quantities': [], 'queries': []}, ''

    @app.callback(
        Output('user-selection', 'data', allow_duplicate=True),
        Input('add-all-flowables-button', 'n_clicks'),
        Input('add-all-contexts-button', 'n_clicks'),
        Input('add-all-quantities-button', 'n_clicks'),
        State('search-results-cache', 'data'),
        State('user-selection', 'data'),
        prevent_initial_call=True
    )
    def add_all_results(n_flowables, n_contexts, n_quantities, search_results, selection_data):
        """Add all results from a column to the selection."""
        from dash import ctx

        if not ctx.triggered_id:
            return no_update

        # Check if this was an actual click
        triggered_value = ctx.triggered[0]['value']
        if triggered_value is None or triggered_value == 0:
            return no_update

        # Create new selection
        new_selection = {
            'flowables': selection_data.get('flowables', []).copy(),
            'contexts': selection_data.get('contexts', []).copy(),
            'quantities': selection_data.get('quantities', []).copy()
        }

        # Add all from the appropriate category
        if ctx.triggered_id == 'add-all-flowables-button':
            for item in search_results.get('flowables', []):
                if item['id'] not in new_selection['flowables']:
                    new_selection['flowables'].append(item['id'])
        elif ctx.triggered_id == 'add-all-contexts-button':
            for item in search_results.get('contexts', []):
                if item['id'] not in new_selection['contexts']:
                    new_selection['contexts'].append(item['id'])
        elif ctx.triggered_id == 'add-all-quantities-button':
            for item in search_results.get('quantities', []):
                if item['id'] not in new_selection['quantities']:
                    new_selection['quantities'].append(item['id'])

        return new_selection
