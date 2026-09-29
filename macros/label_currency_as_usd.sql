{% macro label_currency_as_usd(currency_column) %}
  case when {{ currency_column }} is not null then 'USD' end
{% endmacro %}