from flask import current_app


def add_to_index(index, model):
    if not current_app.elasticsearch:
        return

    payload = {}
    for field in model.__searchable__:
        payload[field] = getattr(model,field)

    current_app.elasticsearch.index(index=index, id=model.id, body=payload)
        # using '.index' method on already existing 'id' replaces old one with new one.


def remove_from_index(index, model):
    if not current_app.elasticsearch:
        return

    current_app.elasticsearch.delete(index=index, id=model.id)


def query_index(index, query, page, per_page):
    if not current_app.elasticsearch:
        return [], 0

    search = current_app.elasticsearch.search(
        index=index,
        body={'query': {'multi_match': {'query': query, 'fields': ['*'] }},
                        #^ search across multiple fields. By passing a field name '*'
                        # I'm telling Elasticsearch to look in all the fields, so
                        # it searches entire index - useful to make this function
                        # generic, since different models can have different
                        # field names in the index.
              'from': (page - 1) * per_page, 'size': per_page # Pagination arguments.
            }
    )
    # List of 'id' elements for the search results
    ids = [ int(hit['_id']) for hit in search['hits']['hits'] ]

    return ids, search['hits']['total']['value']
                # Total number of results.
