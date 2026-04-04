import { X } from "lucide-react";
import { useState, KeyboardEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  maxTags?: number;
  placeholder?: string;
  className?: string;
}

export function TagInput({
  value,
  onChange,
  maxTags = 10,
  placeholder = "输入标签并按回车...",
  className,
}: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key !== "Enter") return;

    e.preventDefault();

    const trimmedValue = inputValue.trim();
    if (!trimmedValue) return;

    // 避免重复标签
    if (value.includes(trimmedValue)) {
      setInputValue("");
      return;
    }

    // 检查最大标签数
    if (value.length >= maxTags) return;

    onChange([...value, trimmedValue]);
    setInputValue("");
  };

  const removeTag = (tagToRemove: string) => {
    onChange(value.filter((tag) => tag !== tagToRemove));
  };

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex flex-wrap gap-2">
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="gap-1 px-2 py-1">
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="ml-1 rounded-full hover:bg-muted p-0.5"
              aria-label={`移除标签 ${tag}`}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
      </div>
      {value.length < maxTags && (
        <Input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="h-9"
        />
      )}
      {value.length >= maxTags && (
        <p className="text-xs text-muted-foreground">
          已达到最大标签数量 ({maxTags})
        </p>
      )}
    </div>
  );
}
