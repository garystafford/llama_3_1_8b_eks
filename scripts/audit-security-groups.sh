#!/bin/bash
# Audit AWS Security Groups for 0.0.0.0/0 ingress rules
# Usage: ./audit-security-groups.sh [vpc-id]

set -e

VPC_ID="${1:-}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"

echo "=== Security Group Audit for 0.0.0.0/0 Rules ==="
echo "Region: $REGION"
if [ -n "$VPC_ID" ]; then
	echo "VPC: $VPC_ID"
	FILTER="--filters Name=vpc-id,Values=$VPC_ID"
else
	echo "VPC: All VPCs"
	FILTER=""
fi
echo ""

# Get all security groups with 0.0.0.0/0 ingress rules
VIOLATIONS=$(aws ec2 describe-security-groups $FILTER \
	--query "SecurityGroups[?IpPermissions[?IpRanges[?CidrIp=='0.0.0.0/0']]].{ID:GroupId,Name:GroupName,VPC:VpcId}" \
	--output json --region "$REGION")

COUNT=$(echo "$VIOLATIONS" | jq length)

if [ "$COUNT" -eq 0 ]; then
	echo "✓ NO security groups have 0.0.0.0/0 ingress rules"
	exit 0
else
	echo "✗ FOUND $COUNT security group(s) with 0.0.0.0/0 ingress rules:"
	echo ""
	echo "$VIOLATIONS" | jq -r '.[] | "  - \(.ID) (\(.Name)) in \(.VPC)"'
	echo ""
	echo "Details:"
	echo ""

	for SG_ID in $(echo "$VIOLATIONS" | jq -r '.[].ID'); do
		echo "--- $SG_ID ---"
		aws ec2 describe-security-groups --group-ids "$SG_ID" --region "$REGION" \
			--query "SecurityGroups[0].IpPermissions[?IpRanges[?CidrIp=='0.0.0.0/0']]" \
			--output table
		echo ""
	done

	exit 1
fi
