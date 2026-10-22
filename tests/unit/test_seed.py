import boto3
from moto import mock_aws
from scripts.seed_policies import seed


@mock_aws
def test_seed_preserves_real_data_and_can_be_repeated():
    table = boto3.resource('dynamodb', region_name='ap-southeast-1').create_table(
        TableName='test-policies', KeySchema=[{'AttributeName':'policy_id','KeyType':'HASH'}],
        AttributeDefinitions=[{'AttributeName':'policy_id','AttributeType':'S'}], BillingMode='PAY_PER_REQUEST')
    table.put_item(Item={'policy_id':'POL-001','title':'Existing owner data'})
    items = [{'policy_id':'POL-001','title':'Fixture'}, {'policy_id':'POL-002','title':'New fixture'}]
    assert seed(table, items) == {'created':1, 'existing_preserved':1}
    assert seed(table, items) == {'created':0, 'existing_preserved':2}
    assert table.get_item(Key={'policy_id':'POL-001'})['Item']['title'] == 'Existing owner data'
