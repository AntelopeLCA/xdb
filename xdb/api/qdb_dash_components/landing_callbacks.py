"""
Landing Page Callbacks

Callbacks for search functionality and result interactions.
"""

from dash import Input, Output, State, html, ALL, ctx
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
        Output('flowables-results', 'children'),
        Output('contexts-results', 'children'),
        Output('quantities-results', 'children'),
        Input('search-button', 'n_clicks'),
        State('search-input', 'value'),
        State('user-selection', 'data'),
        prevent_initial_call=True
    )
    def perform_search(n_clicks, search_query, selection_data):
        """
        Execute search and populate all three result columns.

        Args:
            n_clicks: Number of times search button was clicked
            search_query: The search string
            selection_data: Current user selection

        Returns:
            Tuple of (flowables_results, contexts_results, quantities_results)
        """
        if not search_query or not search_query.strip():
            empty_msg = html.P('Please enter a search term.',
                             className='text-muted', style={'fontStyle': 'italic'})
            return empty_msg, empty_msg, empty_msg

        # Get current selections for each type
        selected_flowables = set(selection_data.get('flowables', []))
        selected_contexts = set(selection_data.get('contexts', []))
        selected_quantities = set(selection_data.get('quantities', []))

        # Search each entity type (STUB calls)
        flowables = list(cat.lcia_engine.flowables(search=search_query))
        contexts = list(cat.lcia_engine.contexts(search=search_query))
        quantities = list(cat.lcia_engine.quantities(search=search_query))

        # Create result items for flowables
        if flowables:
            flowables_results = [
                create_result_item(
                    item.name,  # not ideal, I know
                    '%s (%d terms)' % (item.name, len(item)),
                    'flowable',
                    is_selected=(item.name in selected_flowables)
                )
                for item in flowables
            ]
        else:
            flowables_results = html.P('No flowables found.',
                                      className='text-muted', style={'fontStyle': 'italic'})

        # Create result items for contexts
        if contexts:
            contexts_results = [
                create_result_item(
                    item.fullname,
                    item.name,
                    'context',
                    is_selected=(item.name in selected_contexts)
                )
                for item in contexts
            ]
        else:
            contexts_results = html.P('No contexts found.',
                                     className='text-muted', style={'fontStyle': 'italic'})

        # Create result items for quantities
        if quantities:
            quantities_results = [
                create_result_item(
                    item.uuid,
                    item['name'],
                    'quantity',
                    is_selected=(item.uuid in selected_quantities)
                )
                for item in quantities
            ]
        else:
            quantities_results = html.P('No quantities found.',
                                       className='text-muted', style={'fontStyle': 'italic'})

        return flowables_results, contexts_results, quantities_results

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

        # Add to appropriate list
        if entity_type == 'flowable':
            if entity_id not in selection_data['flowables']:
                selection_data['flowables'].append(entity_id)
        elif entity_type == 'context':
            if entity_id not in selection_data['contexts']:
                selection_data['contexts'].append(entity_id)
        elif entity_type == 'quantity':
            if entity_id not in selection_data['quantities']:
                selection_data['quantities'].append(entity_id)

        return selection_data

    @app.callback(
        Output('flowables-results', 'children', allow_duplicate=True),
        Output('contexts-results', 'children', allow_duplicate=True),
        Output('quantities-results', 'children', allow_duplicate=True),
        Input({'type': 'remove-button', 'index': ALL}, 'n_clicks'),
        State('flowables-results', 'children'),
        State('contexts-results', 'children'),
        State('quantities-results', 'children'),
        prevent_initial_call=True
    )
    def remove_from_results(n_clicks_list, flowables_results, contexts_results, quantities_results):
        """
        Remove an item from the search results display.

        Args:
            n_clicks_list: List of click counts for all remove buttons
            flowables_results: Current flowables results
            contexts_results: Current contexts results
            quantities_results: Current quantities results

        Returns:
            Tuple of updated (flowables_results, contexts_results, quantities_results)
        """
        if not ctx.triggered_id:
            logging.warning('No ctx.triggered_id')
            return flowables_results, contexts_results, quantities_results

        # NEW: Check if this was an actual click (not just initialization)
        triggered_value = ctx.triggered[0]['value']

        # If n_clicks is None or 0, it's just initialization, not a real click
        if triggered_value is None or triggered_value == 0:
            return flowables_results, contexts_results, quantities_results

        # Get the clicked button's index (format: "type:id")
        button_index = ctx.triggered_id['index']
        entity_type, entity_id = button_index.split(':', 1)
        logging.warning('ctx.triggered_id %s entity_type %s entity_id %s' % (ctx.triggered_id['index'], entity_type, entity_id))

        # Helper function to filter out the removed item
        def filter_results(results, entity_type, target_id):
            tgt = '_result_%s_%s' % (entity_type, target_id)
            if isinstance(results, list):
                zuzu = results[0].get('props', {}).get('id', '')
                logging.warning('%s %s' % (results[0]['props']['id'], zuzu == tgt))
                return [item for item in results if not (
                    isinstance(item, dict) and
                    item.get('props', {}).get('id', '') == tgt
                )]
            return results

        # Remove from appropriate column
        if entity_type == 'flowable':
            flowables_results = filter_results(flowables_results, entity_type, entity_id)
            if not flowables_results or (isinstance(flowables_results, list) and len(flowables_results) == 0):
                flowables_results = html.P('No more results in this category.',
                                           className='text-muted', style={'fontStyle': 'italic'})
        elif entity_type == 'context':
            contexts_results = filter_results(contexts_results, entity_type, entity_id)
            if not contexts_results or (isinstance(contexts_results, list) and len(contexts_results) == 0):
                contexts_results = html.P('No more results in this category.',
                                          className='text-muted', style={'fontStyle': 'italic'})
        elif entity_type == 'quantity':
            quantities_results = filter_results(quantities_results, entity_type, entity_id)
            if not quantities_results or (isinstance(quantities_results, list) and len(quantities_results) == 0):
                quantities_results = html.P('No more results in this category.',
                                            className='text-muted', style={'fontStyle': 'italic'})

        return flowables_results, contexts_results, quantities_results
