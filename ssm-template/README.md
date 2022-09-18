# ssm-template

To fetch values out of the AWS SSM Parameter Store and render them in golang template.
When you retrieve them with ssm-template, parameters in latest path will overwrite previous ones.

## Usage

```bash
Usage of ssm-template:
  -path value
    	SSM Parameter path
  -template string
    	renders output from a template file
  -profile string
    	AWS profile
  -region string
    	AWS Region
```

If profile or region is not specified, binary with use default config or AWS role if in EC2.

### Example

Set these SSM paramters by path:
```
/sre/rgate/static_backends/orders/host=http://orders.mesh
/sre/rgate/static_backends/payments/host=http://payments.mesh
/sre/demo-service/db_password=XXX
/sre/demo-service/db_host=mydb.io
```

To get all values as JSON (default)

```bash
    > ssm-template -path /sre/rgate/static_backends/orders -path /sre/rgate/static_backends/payments -path /sre/demo-service

    {
      "host": "http://payments.mesh",
      "db_password": "XXX"
      "db_host": "mydb.io"
    }
```

To get all values in template

```bash
    > echo "DB_HOSTNAME={{.db_host}}, DB_PASSWORD={{.db_password}}" > example.tpl
    > ssm-template -template example.tpl -path /sre/rgate/static_backends/orders -path /sre/rgate/static_backends/payments -path /sre/demo-service

      DB_HOSTNAME=mydb.io, DB_PASSWORD=XXX
```

## Build

To build the darwin binary

```bash
  > make build-darwin
```

To build the linux binary

```bash
  > make build-linux
```
