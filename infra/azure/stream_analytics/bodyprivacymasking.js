
// Javascript UDF 함수
// Name: bodyprivacymasking
// Stream Analytics의 UDF로 해당 함수를 입력해야 한다.

// Sample UDF which returns sum of two values.
function main(text) {
    if (!text) return null;

    var result = text;

    /* 이메일 마스킹 */
    result = result.replace(
        /([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g,
        function(match, name, domain) {
            if (name.length <= 2) {
                return name[0] + "*@" + domain;
            }
            var masked =
                name[0] +
                "*".repeat(name.length - 2) +
                name[name.length - 1];
            return masked + "@" + domain;
        }
    );

    /* 전화번호 마스킹 (한국) */
    result = result.replace(
        /(01[0-9]|02|0[3-9][0-9])[-]?\d{3,4}[-]?\d{4}/g,
        function(match) {
            var digits = match.replace(/[^0-9]/g, '');
            return digits.substring(0, 3) +
                   "****" +
                   digits.substring(digits.length - 4);
        }
    );
    return result;
}
