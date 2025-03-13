Chamba AI es un webscraper de Linkedin combinado con el api de Gemini. Utiliza selenium para guardar trabajos coincidentes con una lista de keywords, y los guarda en un json.

Después gemini se encarga de revisar cada empleo y compararlo con mi curriculum, finalmente recomienda aquellos que mejor coinciden con mi perfil y objetivo profesional, en un ranking del 1 al 10.

Todo esto se presenta en una pequeña app local con flask.

Futuras mejoras incluyen la integración de otros portales de empleo, la entrada automatica del curriculum y la iteración con diferentes prompts especializados.
