/* custom request template for openapi-typescript-codegen axios client */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import axios from 'axios';
import type { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

import { ApiError } from './ApiError';
import type { ApiRequestOptions } from './ApiRequestOptions';
import type { ApiResult } from './ApiResult';
import { CancelablePromise } from './CancelablePromise';
import type { OnCancel } from './CancelablePromise';
import type { OpenAPIConfig } from './OpenAPI';

export const isDefined = <T>(value: T | null | undefined): value is Exclude<T, null | undefined> => {
    return value !== undefined && value !== null;
};

export const isString = (value: unknown): value is string => {
    return typeof value === 'string';
};

export const isStringWithValue = (value: unknown): value is string => {
    return isString(value) && value !== '';
};

export const isBlob = (value: unknown): value is Blob => {
    if (typeof value !== 'object' || value === null) {
        return false;
    }

    const blob = value as Blob;
    return typeof blob.type === 'string' && typeof blob.arrayBuffer === 'function';
};

export const isFormData = (value: unknown): value is FormData => {
    return typeof FormData !== 'undefined' && value instanceof FormData;
};

export const isSuccess = (status: number): boolean => {
    return status >= 200 && status < 300;
};

export const base64 = (str: string): string => {
    if (typeof btoa === 'function') {
        return btoa(str);
    }

    throw new Error('Base64 encoding is not supported in this environment.');
};

export const getQueryString = (params: Record<string, unknown>): string => {
    const qs: string[] = [];

    const append = (key: string, value: unknown) => {
        qs.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    };

    const process = (key: string, value: unknown) => {
        if (!isDefined(value)) {
            return;
        }

        if (Array.isArray(value)) {
            value.forEach((item) => {
                process(key, item);
            });
            return;
        }

        if (value !== null && typeof value === 'object') {
            Object.entries(value).forEach(([nestedKey, nestedValue]) => {
                process(`${key}[${nestedKey}]`, nestedValue);
            });
            return;
        }

        append(key, value);
    };

    Object.entries(params).forEach(([key, value]) => {
        process(key, value);
    });

    return qs.length > 0 ? `?${qs.join('&')}` : '';
};

const getUrl = (config: OpenAPIConfig, options: ApiRequestOptions): string => {
    const encoder = config.ENCODE_PATH || encodeURI;
    const path = options.url
        .replace('{api-version}', config.VERSION)
        .replace(/{(.*?)}/g, (substring: string, group: string) => {
            if (options.path?.hasOwnProperty(group)) {
                return encoder(String(options.path[group]));
            }
            return substring;
        });

    const url = `${config.BASE}${path}`;
    return options.query ? `${url}${getQueryString(options.query)}` : url;
};

export const getFormData = (options: ApiRequestOptions): FormData | undefined => {
    if (!options.formData) {
        return undefined;
    }

    const formData = new FormData();

    const process = (key: string, value: unknown) => {
        if (isString(value) || isBlob(value)) {
            formData.append(key, value);
            return;
        }

        formData.append(key, JSON.stringify(value));
    };

    Object.entries(options.formData)
        .filter(([, value]) => isDefined(value))
        .forEach(([key, value]) => {
            if (Array.isArray(value)) {
                value.forEach((item) => process(key, item));
                return;
            }
            process(key, value);
        });

    return formData;
};

type Resolver<T> = (options: ApiRequestOptions) => Promise<T>;

export const resolve = async <T>(options: ApiRequestOptions, resolver?: T | Resolver<T>): Promise<T | undefined> => {
    if (typeof resolver === 'function') {
        return (resolver as Resolver<T>)(options);
    }
    return resolver;
};

export const getHeaders = async (
    config: OpenAPIConfig,
    options: ApiRequestOptions,
    formData?: FormData
): Promise<Record<string, string>> => {
    const [token, username, password, additionalHeaders] = await Promise.all([
        resolve(options, config.TOKEN),
        resolve(options, config.USERNAME),
        resolve(options, config.PASSWORD),
        resolve(options, config.HEADERS),
    ]);

    const headers = Object.entries({
        Accept: 'application/json',
        ...additionalHeaders,
        ...options.headers,
    })
        .filter(([, value]) => isDefined(value))
        .reduce((result, [key, value]) => ({
            ...result,
            [key]: String(value),
        }), {} as Record<string, string>);

    if (isStringWithValue(token)) {
        headers.Authorization = `Bearer ${token}`;
    }

    if (isStringWithValue(username) && isStringWithValue(password)) {
        headers.Authorization = `Basic ${base64(`${username}:${password}`)}`;
    }

    if (!formData && options.body !== undefined) {
        if (options.mediaType) {
            headers['Content-Type'] = options.mediaType;
        } else if (isBlob(options.body)) {
            headers['Content-Type'] = options.body.type || 'application/octet-stream';
        } else if (isString(options.body)) {
            headers['Content-Type'] = 'text/plain';
        } else if (!isFormData(options.body)) {
            headers['Content-Type'] = 'application/json';
        }
    }

    return headers;
};

export const getRequestBody = (options: ApiRequestOptions): unknown => {
    return options.body;
};

export const sendRequest = async <T>(
    config: OpenAPIConfig,
    options: ApiRequestOptions,
    url: string,
    body: unknown,
    formData: FormData | undefined,
    headers: Record<string, string>,
    onCancel: OnCancel,
    axiosClient: AxiosInstance
): Promise<AxiosResponse<T>> => {
    const source = axios.CancelToken.source();

    const requestConfig: AxiosRequestConfig = {
        url,
        headers,
        data: body ?? formData,
        method: options.method,
        withCredentials: config.WITH_CREDENTIALS,
        withXSRFToken: config.CREDENTIALS === 'include' ? config.WITH_CREDENTIALS : false,
        cancelToken: source.token,
    };

    onCancel(() => source.cancel('The user aborted a request.'));

    try {
        return await axiosClient.request(requestConfig);
    } catch (error) {
        const axiosError = error as AxiosError<T>;
        if (axiosError.response) {
            return axiosError.response;
        }
        throw error;
    }
};

export const getResponseBody = (response: AxiosResponse<unknown>): unknown => {
    if (response.status !== 204) {
        return response.data;
    }
    return undefined;
};

export const catchErrorCodes = (options: ApiRequestOptions, result: ApiResult): void => {
    const errors: Record<number, string> = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        500: 'Internal Server Error',
        502: 'Bad Gateway',
        503: 'Service Unavailable',
        ...options.errors,
    };

    const error = errors[result.status];
    if (error) {
        throw new ApiError(options, result, error);
    }

    if (!result.ok) {
        throw new ApiError(options, result, 'Generic Error');
    }
};

export const request = <T>(config: OpenAPIConfig, options: ApiRequestOptions): CancelablePromise<T> => {
    return new CancelablePromise(async (resolvePromise, rejectPromise, onCancel) => {
        try {
            const axiosClient = (config.HEADERS as { axiosClient?: AxiosInstance } | undefined)?.axiosClient ?? axios;
            const url = getUrl(config, options);
            const formData = getFormData(options);
            const body = getRequestBody(options);
            const headers = await getHeaders(config, options, formData);

            if (!onCancel.isCancelled) {
                const response = await sendRequest<T>(config, options, url, body, formData, headers, onCancel, axiosClient);
                const responseBody = getResponseBody(response);
                const result: ApiResult = {
                    url,
                    ok: isSuccess(response.status),
                    status: response.status,
                    statusText: response.statusText,
                    body: responseBody,
                };

                catchErrorCodes(options, result);

                resolvePromise(responseBody as T);
            }
        } catch (error) {
            rejectPromise(error);
        }
    });
};
