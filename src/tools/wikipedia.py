import wikipedia

def search_wikipedia(query: str) -> list[str]:
    """
    Search Wikipedia for articles matching the query.
    
    Args:
        query: The search term to look up on Wikipedia
    
    Returns:
        A list of article titles matching the search query
    """
    return wikipedia.search(query)