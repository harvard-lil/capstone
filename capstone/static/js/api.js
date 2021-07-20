import {encodeQueryData} from './utils';


export function getApiUrl(api_url, endpoint, params) {
  return `${api_url}${endpoint}/?${encodeQueryData(params)}`;
}

export function getApiUrlNoEncode(api_url, endpoint, params) {
  return `${api_url}${endpoint}/?${params}`;
}

export function jsonQuery(url) {
  return fetch(url).then((resp) => {
      if (!resp.ok)
        throw resp;
      return resp.json();
    })
}