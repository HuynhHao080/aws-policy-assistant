"""Grant the selected owner admin access only after email confirmation."""
import argparse
import boto3

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--email", required=True)
parser.add_argument("--stack", default="policy-assistant")
args = parser.parse_args()
cf = boto3.client("cloudformation", region_name="ap-southeast-1")
outputs = {v["OutputKey"]: v["OutputValue"] for v in cf.describe_stacks(StackName=args.stack)["Stacks"][0]["Outputs"]}
pool = outputs["UserPoolId"]
client = boto3.client("cognito-idp", region_name="ap-southeast-1")
if any(c in args.email for c in ('"', "\\")):
    raise SystemExit("Invalid email address")
users = client.list_users(UserPoolId=pool, Filter=f'email = "{args.email}"', Limit=2)["Users"]
if len(users) != 1:
    raise SystemExit("Register the selected email on the website and confirm it before granting admin access.")
user = users[0]
attrs = {v["Name"]: v["Value"] for v in user.get("Attributes", [])}
if user["UserStatus"] != "CONFIRMED" or attrs.get("email_verified") != "true" or not user.get("Enabled"):
    raise SystemExit("The selected account must be active with a confirmed email.")
client.admin_add_user_to_group(UserPoolId=pool, Username=user["Username"], GroupName="administrators")
print("Administrator role granted to the confirmed selected account. Sign out and sign in again to refresh permissions.")
