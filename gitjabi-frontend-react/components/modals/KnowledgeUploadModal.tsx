import React, { useState } from 'react';
import { Upload, X, FileText, CheckCircle2, Loader2 } from 'lucide-react';
import api from '../../api/api';

const KnowledgeUploadModal = ({ isOpen, onClose }) => {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/api/knowledge/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("지식 데이터가 성공적으로 ADLS에 업로드되었습니다. 잠시 후 분석이 시작됩니다!");
      onClose();
    } catch (err) {
      alert("업로드 실패: " + (err.response?.data?.detail || "서버 오류"));
    } finally {
      setIsUploading(false);
      setFile(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-lg bg-white dark:bg-card-dark rounded-3xl shadow-2xl border border-gray-100 dark:border-gray-800 p-10 space-y-8 animate-in fade-in zoom-in-95 duration-200">
        
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black flex items-center gap-2">
              <Upload size={20} className="text-primary"/>
              지식 데이터 등록
            </h2>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mt-1">Upload Compliance Documents</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg text-gray-400 hover:text-red-500 transition-colors"><X size={18}/></button>
        </div>

        <div className="space-y-6">
          <div className={`border-2 border-dashed rounded-2xl p-8 transition-all flex flex-col items-center justify-center gap-4 ${file ? 'border-primary bg-primary/5' : 'border-gray-200 hover:border-primary/40'}`}>
            {file ? (
              <>
                <FileText size={40} className="text-primary" />
                <div className="text-center">
                  <p className="text-sm font-bold text-gray-700">{file.name}</p>
                  <p className="text-[10px] text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </>
            ) : (
              <>
                <div className="p-4 bg-gray-50 rounded-full"><Upload size={24} className="text-gray-400" /></div>
                <div className="text-center space-y-1">
                  <p className="text-sm font-bold">분석할 파일을 선택하세요</p>
                  <p className="text-xs text-gray-400">PDF, TXT, MD 파일 지원</p>
                </div>
              </>
            )}
            <input type="file" id="file-upload" className="hidden" onChange={handleFileChange} accept=".pdf,.txt,.md" />
            <label htmlFor="file-upload" className="cursor-pointer text-xs font-black text-primary hover:underline">파일 찾아보기</label>
          </div>
          
          <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl flex gap-3">
            <CheckCircle2 size={16} className="text-blue-500 shrink-0 mt-0.5" />
            <p className="text-[10px] leading-relaxed text-blue-700 dark:text-blue-300">
              업로드된 파일은 **Azure Data Lake Storage**의 <code>gitjabi_raw</code> 디렉토리로 안전하게 전송되며, 
              자동화된 **Auto Loader**가 실시간으로 분석하여 지식 그래프에 반영합니다.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-4 pt-4 border-t border-gray-100">
          <button onClick={onClose} className="px-5 py-2 rounded-xl text-xs font-bold text-gray-500 hover:bg-gray-50">취소</button>
          <button 
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="px-6 py-2 rounded-xl bg-primary text-white text-xs font-black shadow-lg disabled:opacity-50 transition-all flex items-center gap-2"
          >
            {isUploading ? <><Loader2 size={14} className="animate-spin" /> 전송 중...</> : "등록 및 분석 시작"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeUploadModal;