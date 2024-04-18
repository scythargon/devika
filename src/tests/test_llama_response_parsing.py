from src.utils import parse_llm_response_to_json, parse_xml_llm_response, parse_xml_llm_response_commands


def test_1():
    resp = '{\n"response": "To get a list of databases in PostgreSQL using psql or SQL, you can use the following command: `\\list` or `SELECT datname FROM pg_database;` respectively in your psql terminal or SQL client.",\n"action": "answer"\n}'
    j = parse_llm_response_to_json(resp)
    assert isinstance(j, dict)


def test_2():
    resp = """
    ```json
{
    "response": "To get a list of databases in PostgreSQL using the psql CLI tool without any parameters, open your terminal and type `psql` followed by the name of your PostgreSQL database if you're connected to a specific one. If not, press enter to connect to the default database. Once connected, use the command `\list` or press the tab key twice to see a list of all databases."
}
```
    """
    j = parse_llm_response_to_json(resp)
    assert isinstance(j, dict)


# def test_3():
#     resp = """
# ```json
# {
#     "response": "To get a list of databases in PostgreSQL using SQL or psql, you can use the following command: \n\
#              - For SQL:\n\
#              SELECT pg_database.datname FROM pg_database WHERE pg_database.datist temple = false;\n\
#              \n- For psql:\n\
#              \\list\nOR\n\
#              \SELECT name FROM pg_catalog.pg\_database WHERE datname !='template0' AND datname !='template1';"
# }
# ```
#     """
#     j = parse_llm_response_to_json(resp)
#     assert isinstance(j, dict)
#
#
# def test_4():
#     resp = """
# {
# "response": "I will now execute the command 'psql -c "SELECT * FROM pg_database;"" in your terminal to display the list of databases in PostgreSQL.",
# "action": "execute"
# }
#     """
#     j = parse_llm_response_to_json(resp)
#     assert isinstance(j, dict)
#

def test_xml_1():
    xml_resp = '''
    <command>
      <response>I will now execute the command 'psql -c "SELECT * FROM pg_database;"' in your terminal to display the list of databases in PostgreSQL.</response>
      <action>execute</action>
    </command>
    '''
    j = parse_xml_llm_response(xml_resp)
    assert isinstance(j, dict)


def test_xml_2():
    xml_resp = '''
        <commands>
          <command>pip3 install -r requirements.txt</command>
          <command>python3 main.py</command>
        </commands>
    '''
    j = parse_xml_llm_response_commands(xml_resp)
    assert isinstance(j, dict)
    assert "commands" in j


def test_xml_3():
    xml_resp = '''
        <root>
          <action>command</action>
          <command><![CDATA[Fixed command here]]></command>
          <response><![CDATA[A response like: I encountered an error while running the project. Seems to be {problem}. Let me try fixing it.]]></response>
        </root>
    '''
    j = parse_xml_llm_response(xml_resp)
    assert isinstance(j, dict)
    assert "action" in j
    assert "command" in j
    assert "response" in j


def test_xml_4():
    xml_resp = '''
<root>
 <command><![CDATA[echo 'Getting list of databases in PostgreSQL using psql' && psql -c '\list' | awk '{print $1}']]></command>
</root>
    '''
    j = parse_xml_llm_response(xml_resp)
    assert isinstance(j, dict)
