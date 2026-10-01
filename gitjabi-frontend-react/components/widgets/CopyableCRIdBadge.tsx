import { useState } from 'react';
import { Copy, Check } from 'lucide-react'; // 아이콘 라이브러리 (선택)

const CrIdBadge = ({ crId }: { crId: string }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(crId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('복사 실패:', err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="group relative flex items-center justify-center px-6 py-1.5 rounded-full 
                 bg-primary/10 border border-primary/20 text-primary 
                 hover:bg-primary/20 transition-all duration-200 active:scale-95
                 min-w-[140px]" // 버튼 너비를 고정하면 글자 흔들림이 완벽히 방지됩니다.
    >
      {/* CR ID: 항상 중앙 정렬 */}
      <span className="text-xs font-black tracking-widest uppercase">
        {crId}
      </span>
      
      {/* 아이콘 영역: absolute 배치로 글자 위치에 영향을 주지 않음 */}
      <div className="absolute right-3 flex items-center justify-center">
        {copied ? (
          <Check size={14} className="text-green-500 animate-in zoom-in duration-300" />
        ) : (
          <Copy size={14} className="opacity-0 group-hover:opacity-100 transform translate-x-1 group-hover:translate-x-0 transition-all duration-200" />
        )}
      </div>

      {/* 복사 완료 툴팁 */}
      {copied && (
        <div className="absolute -top-9 left-1/2 -translate-x-1/2 px-2.5 py-1 
                        bg-gray-900 text-white text-[10px] rounded-md shadow-xl 
                        animate-in fade-in slide-in-from-bottom-1 duration-200 font-bold">
          COPIED!
        </div>
      )}
    </button>
  );
};
export default CrIdBadge;