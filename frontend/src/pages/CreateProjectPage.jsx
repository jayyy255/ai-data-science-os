import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useProjectStore } from '../store/useProjectStore';
import { ArrowLeft, Upload, FileCode, CheckCircle2, RefreshCw, AlertCircle } from 'lucide-react';

export default function CreateProjectPage() {
  const navigate = useNavigate();
  const createProject = useProjectStore((state) => state.createProject);

  const [projectName, setProjectName] = useState('');
  const [targetVariable, setTargetVariable] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [completed, setCompleted] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      simulateUpload(selectedFile);
    }
  };

  const simulateUpload = (selectedFile) => {
    setUploading(true);
    setUploadProgress(0);
    setCompleted(false);
    
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setUploading(false);
          setCompleted(true);
          return 100;
        }
        return prev + 20;
      });
    }, 200);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) {
      alert('Please upload a dataset CSV first.');
      return;
    }
    
    // Create the project in the store
    createProject(
      projectName,
      targetVariable,
      description,
      file,
      file.name,
      (file.size / (1024 * 1024)).toFixed(2) + ' MB'
    );

    // Navigate back to overview of newly created project
    navigate('/overview');
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link 
          to="/"
          className="p-2 bg-brand-dark-surface hover:bg-brand-dark-card border border-brand-dark-border text-zinc-400 hover:text-zinc-200 rounded-xl transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-2xl font-display font-bold text-white tracking-tight">Create New AI Project</h1>
          <p className="text-xs text-zinc-400">Initialize storage buckets and trigger the Gemini project understanding engine.</p>
        </div>
      </div>

      {/* Form Card */}
      <form onSubmit={handleSubmit} className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-6 space-y-5 shadow-xl">
        
        {/* Project Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Project Name</label>
            <input
              type="text"
              id="project-name"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 px-3 rounded-xl text-sm font-medium transition-all"
              placeholder="e.g. Demand Forecasting"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-zinc-400">Target Variable Column</label>
            <input
              type="text"
              id="target-variable"
              value={targetVariable}
              onChange={(e) => setTargetVariable(e.target.value)}
              className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 px-3 rounded-xl text-sm font-medium transition-all font-mono"
              placeholder="e.g. sales_quantity"
              required
            />
          </div>
        </div>

        {/* Business Goal Description */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">Business Problem Description</label>
          <textarea
            value={description}
            id="project-description"
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 px-3 rounded-xl text-sm font-medium transition-all leading-relaxed"
            placeholder="Describe the target outcomes and goals..."
          />
        </div>

        {/* File Drag & Drop Zone */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-zinc-400">Upload Raw Dataset (CSV)</label>
          <div className="border-2 border-dashed border-brand-dark-border hover:border-violet-500/40 rounded-xl p-8 flex flex-col items-center justify-center text-center bg-brand-dark-bg/30 relative">
            <input
              type="file"
              id="dataset-upload"
              accept=".csv"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              disabled={uploading}
            />
            
            {!file ? (
              <div className="space-y-2">
                <div className="bg-brand-dark-card p-3 rounded-full border border-brand-dark-border text-zinc-500 inline-block">
                  <Upload className="w-6 h-6" />
                </div>
                <p className="text-sm font-medium text-zinc-300">Drag & drop your CSV file here, or click to browse</p>
                <p className="text-xs text-zinc-500">Max file size: 50MB (saved locally in MinIO)</p>
              </div>
            ) : (
              <div className="w-full space-y-4">
                <div className="flex items-center gap-3 bg-brand-dark-card p-3 rounded-xl border border-brand-dark-border text-left">
                  <div className="bg-violet-500/10 p-2 rounded-lg text-violet-400">
                    <FileCode className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-zinc-200 truncate">{file.name}</p>
                    <p className="text-xs text-zinc-500 font-mono">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                  </div>
                  
                  {uploading && (
                    <RefreshCw className="w-4 h-4 text-brand-primary animate-spin" />
                  )}
                  {completed && (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  )}
                </div>

                {uploading && (
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-mono text-zinc-500">
                      <span>Uploading to MinIO S3...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-brand-dark-card h-1.5 rounded-full overflow-hidden">
                      <div 
                        className="bg-brand-primary h-full transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                
                {completed && (
                  <p className="text-xs text-emerald-400 font-semibold flex items-center justify-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" />
                    Dataset successfully uploaded and registered in MinIO s3://datasets/{file.name}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-4 border-t border-brand-dark-border/40">
          <div className="flex items-center gap-1.5 text-[10px] text-zinc-500 font-mono">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>PostgreSQL & MinIO S3 will be synchronized.</span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="bg-brand-dark-card border border-brand-dark-border hover:bg-brand-dark-border px-5 py-2 rounded-xl text-xs font-bold text-zinc-300 transition-all cursor-pointer"
            >
              Cancel
            </Link>
            <button
              type="submit"
              id="project-submit"
              disabled={!file || uploading}
              className={`
                px-5 py-2 rounded-xl text-xs font-bold text-white transition-all shadow-lg cursor-pointer
                ${(!file || uploading) 
                  ? 'bg-zinc-700/50 text-zinc-500 cursor-not-allowed border border-transparent shadow-none' 
                  : 'bg-brand-primary hover:bg-brand-primary-hover border border-transparent shadow-brand-primary/25'}
              `}
            >
              Initialize Project
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
