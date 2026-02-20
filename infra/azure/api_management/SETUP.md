# Azure API Management

API Gateway를 구성함으로 안정된 구조, 보안성을 향상 시킨다.

```plaintext
Github <--> APIM <--> Backend API

Users <--> APIM <--> Backend API
```

## 이벤트 허브 로깅

이벤트 허브 로그는 내부적으로 logger를 생성하고 연결시켜주어야 한다.

CLI 방식도 있지만, MS 공식 문서에 따라 API로 호출하여도 된다.

해당 URL을 Postman에서 사용할 수 있다.

```plaintext
https://management.azure.com/subscriptions/{{subscriptionId}}/resourceGroups/{{resourceGroupName}}/providers/Microsoft.ApiManagement/service/{{serviceName}}/loggers/{{loggerId}}?api-version=2024-05-01
```

각 {} 안에 Identity 정보와 필요한 값들을 입력한다.

그 후, 보내는 Body의 내용은 아래 양식에 따라 지정하며, loggerId는 생성하기 원하는 로거 이름을 지정하는 것이다.

```json
{
  "properties": {
    "loggerType": "azureEventHub",
    "description": "GitHub Webhook 로그 수집용 Logger",
    "credentials": {
      "name": "gitjabi-eventhub",
      "connectionString": "Endpoint=sb://dt-team2-eh.servicebus.windows.net/;SharedAccessKeyName=RootManagedAccessKey;SharedAccessKey=******************************=;EntityPath=gitjabi-eventhub"
    },
    "isBuffered": false
  }
}
```

(AccessKey는 *로 마스킹 처리 하였음.)

이벤트 허브와 연결시킬 것이기 때문에, 네임스페이스와 이벤트허브 인스턴스 명을 입력한다.
`gitjabi-eventhub`는 인스턴스 명, `dt-team2-eh`는 네임스페이스 명이다.
내부적으로 RootManagedAccessKey라는 연결 문자열을 생성하고 connectionString으로 입력하면 간단하다.

헤더는 아래와 같이 지정하며, 엑세스 토큰은 별도로 CLI를 통해 발급받거나, F12 개발자 모드에서 임시적으로 추출 하여 사용할 수 있다.

```plaintext
Content-Type:application/json
Authorization:Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1N...
```

Params로는 `?api-version=2024-05-01`와 같이 지정해야 한다.

200 OK를 확인 후 생성이 완료된 경우 이제 APIM 내부적으로 로거를 호출 가능하다.

그 후 내가 원하는 내부 API의 인바운드 정책을 아래와 같이 지정하면 된다.

정책에 대해 모르는 경우 `2_APIs.png` 파일을 참조하여 확인하면 된다.

```xml
<policies>
    <!-- Throttle, authorize, validate, cache, or transform the requests -->
    <inbound>
        <base />
        <log-to-eventhub logger-id="eventhublogger">@{
        string eventType = context.Request.Headers.GetValueOrDefault("X-GitHub-Event", "unknown");
        // 원본 body
        string rawBody = context.Request.Body.As<string>(preserveContent: true);
        var parsedBody = Newtonsoft.Json.Linq.JObject.Parse(rawBody);
        var finalObject = new Newtonsoft.Json.Linq.JObject();
        finalObject["event_type"] = eventType;
        finalObject["received_at"] = DateTime.UtcNow;
        finalObject["payload"] = parsedBody;
        return finalObject.ToString();
    }</log-to-eventhub>
    </inbound>
    <!-- Control if and how the requests are forwarded to services  -->
    <backend>
        <base />
    </backend>
    <!-- Customize the responses -->
    <outbound>
        <base />
    </outbound>
    <!-- Handle exceptions and customize error responses  -->
    <on-error>
        <base />
    </on-error>
</policies>
```

## 프록시 API (Github API) 설정

`내부 백엔드 (HTTP) <--> APIM <--> Github API`

위와 같은 구조를 만들기 위해 프록시 구조를 설정한다.

APIM을 이용하면, 백엔드에서는 api_management/api/github-api-proxy  주소를 통해 중간 Proxy 형태로 모든 호출을 송수신받을 수 있다.

![그림_1](./3_API_proxy_github.png)

![그림_2](./3_API_proxy_github_2.png)

**정책은 다음과 같이 설정한다.**

```xml
<!--
    - Policies are applied in the order they appear.
    - Position <base/> inside a section to inherit policies from the outer scope.
    - Comments within policies are not preserved.
-->
<!-- Add policies as children to the <inbound>, <outbound>, <backend>, and <on-error> elements -->
<policies>
    <!-- Throttle, authorize, validate, cache, or transform the requests -->
    <inbound>
        <base />
        <set-backend-service base-url="https://api.github.com" />
        <set-header name="User-Agent" exists-action="skip">
            <value>Azure-APIM-Proxy</value>
        </set-header>
    </inbound>
    <!-- Control if and how the requests are forwarded to services  -->
    <backend>
        <forward-request />
    </backend>
    <!-- Customize the responses -->
    <outbound>
        <base />
    </outbound>
    <!-- Handle exceptions and customize error responses  -->
    <on-error>
        <base />
    </on-error>
</policies>
```

**APIM 특성상 `Operations`를 메서드 별로 만들어야 함을 참고해야 한다.**

![그림_3](./3_API_proxy_github_3.png)

또한, 메서드의 엔드포인트를 `/*`으로 지정함으로 모든 엔드포인트를 그대로 전달하도록 한다.

GET과 똑같이 나머지 메서드도 생성하면 끝.
