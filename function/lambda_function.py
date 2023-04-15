import logging
import urllib.parse
import boto3
import random
import string

SSN_FIELD = 1
SSN_TOKEN_LEN = 9


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3Client = boto3.client('s3')
ddbClient = boto3.client('dynamodb')

client = boto3.client('lambda')
client.get_account_settings()

def lambda_handler(event, context):
    deid_file = "";
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    srcFileName = key.split('/')[1]
    try:
        for line in s3Client.get_object(Bucket=bucket, Key=key)['Body'].iter_lines(): 
            splitLine = line.decode('utf-8').split(",")
            token = getToken(ddbClient, "ssnMap", splitLine[SSN_FIELD])
            if token is None:
                newToken = generateToken(SSN_TOKEN_LEN)
                putToken(ddbClient, "ssnMap", "ssn", splitLine[SSN_FIELD], newToken)
                splitLine[SSN_FIELD] = newToken
                newLine = ','.join(splitLine)
                newLine += '\n'
                deid_file += newLine
                print(','.join(splitLine))
            else:
                splitLine[SSN_FIELD] = token
                newLine = ','.join(splitLine)
                newLine += '\n'
                deid_file += newLine
                print(','.join(splitLine))
        s3Client.put_object(
            Body=deid_file.encode('utf-8'),
            Bucket=bucket,
            Key='outbound/'+srcFileName)

    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

def getToken(client, table, keyVal):
    print("Getting with key: " + keyVal + " in table: " + table)
    response = client.get_item(TableName = table,
    Key = {
        'ssn': {
            'S': keyVal
        }
    })
    if "Item" in response:
        return response["Item"]["token"]["S"]
    else:
        return None


def putToken(client, table, key, keyVal, tokenVal):
    print("Putting key: " + key + " with value: " + keyVal + " in table: " + table)
    data = client.put_item(TableName=table, 
      Item = {
        key: {
            'S': keyVal
        },
        'token': {
            'S': tokenVal
        }
      }
    )

def generateToken(tokenLen):
    return ''.join(random.choices(string.digits, k=tokenLen))
   
