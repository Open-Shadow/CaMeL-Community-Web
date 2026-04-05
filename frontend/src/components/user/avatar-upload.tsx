import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { api } from '@/hooks/use-auth';

interface AvatarUploadProps {
  currentUrl?: string;
  displayName?: string;
  onSuccess?: (url: string) => void;
}

export function AvatarUpload({ currentUrl, displayName, onSuccess }: AvatarUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState(currentUrl || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Client-side validation
    if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
      setError('仅支持 JPG、PNG、GIF、WebP 格式'); return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError('文件大小不能超过 2MB'); return;
    }

    // Preview
    setPreview(URL.createObjectURL(file));
    setError('');
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/users/me/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onSuccess?.(res.data.avatar_url);
    } catch (err: any) {
      setError(err.response?.data?.message || '上传失败');
      setPreview(currentUrl || '');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      <Avatar className="h-16 w-16">
        <AvatarImage src={preview} />
        <AvatarFallback>{displayName?.[0]?.toUpperCase()}</AvatarFallback>
      </Avatar>
      <div className="space-y-1">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isLoading}
          onClick={() => inputRef.current?.click()}
        >
          {isLoading ? '上传中...' : '更换头像'}
        </Button>
        <p className="text-xs text-muted-foreground">JPG/PNG/WebP，最大 2MB</p>
        {error && <p className="text-xs text-red-500">{error}</p>}
        <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={handleFileChange} />
      </div>
    </div>
  );
}
