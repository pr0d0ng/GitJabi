
// Javascript UDF 함수
// Name: parselabels
// Stream Analytics의 UDF로 해당 함수를 입력해야 한다.

function main(arr) {
    if(!arr) return null;
    return arr.map(x => x.name).join(','); 
}