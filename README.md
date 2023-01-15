# RSI Star Citizen LTI Discord Report

## **Background**
[Lifetime insurance](https://starcitizen.fandom.com/wiki/Lifetime_Insurance#:~:text=Lifetime%20Insurance%20(LTI)%20is%20a,from%20one%20ship%20to%20another.) is an insurance package that comes with some ships pledged in star citizen. These ships are highly saught after even though they may not be pivital to gameplay in the future. These ships come and go from the [pledge store](http://robertsspaceindustries.com/pledge/ships/). It is difficult to know what ships currently have LTI. I created this lambda function to alert once a month to ships with LTI.

## **Deployment**
![overview](/readme-images/function-overview.png)
![config](/readme-images/general%20config.png)

This was written with the intent of running in an AWS lambda function. The usage is so small and infrequent enough that it does not exceed free tier.

I setup a python lambda function and have an event triggered on the last day of every month
- cron(0 10 L * ? *)


### **Environment variables**
| Variable      | Description |
| ----------- | ----------- |
| DISCORD_MENTION_ROLE_ID      | Role ID to mention with every publish       |
| DISCORD_WEBHOOK_URL   | Webhook URL to send the alert to        |

### **Event variables**
| Variable      | Description |
| ----------- | ----------- |
| dryrun      | If true, logs output to console       |