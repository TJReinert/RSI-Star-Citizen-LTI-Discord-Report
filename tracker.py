import urllib.request
import json
import os

base_uri = "https://robertsspaceindustries.com"
graphql_uri = f"{base_uri}/graphql"
webhook_uri = os.environ.get('DISCORD_WEBHOOK_URL')
discord_message_mention = os.environ.get('DISCORD_MENTION_ROLE_ID')


def execute():
    ships = get_lti_pledge_ships_page()
    task = send_discord_notification(ships)
    print(f"Sent request with status code: {task.status}")


def data_to_bytes(obj):
    return str(json.dumps(obj)).encode("utf-8")


def get_lti_pledge_ships_page(page=1):
    print(f"Fetching page number {page}")
    limit = 20
    payload = _create_query_payload(page=page, limit=limit)
    response = urllib.request.urlopen(urllib.request.Request(
        method="POST",
        url=graphql_uri,
        headers={
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json'
        },
        data=data_to_bytes(payload)
    ))

    lti_ships = []
    for datum in json.loads(response.read()):
        if datum['data'] is not None:
            if datum['data']['store'] is not None:
                if datum['data']['store']['listing'] is not None:
                    if datum['data']['store']['listing']['resources'] is not None:
                        resources = datum['data']['store']['listing']['resources']
                        for ship in resources:
                            if ship is not None:
                                if "lifetime insurance" in ship['excerpt']:
                                    lti_ships.append(ship)

    is_last = len(resources) is not limit

    if is_last:
        if lti_ships is None or len(lti_ships) == 0:
            return []
        return lti_ships
    else:
        lti_ships.extend(get_lti_pledge_ships_page(page=page+1))
        return lti_ships


def _create_query_payload(limit=20, page=1):
    return [
        {
            "operationName": "GetBrowseListingQuery",
            "variables": {
                "query": {
                    "skus": {
                        "products": [
                            "72"
                        ]
                    },
                    "limit": limit,
                    "page": page,
                    "sort": {
                        "field": "weight",
                        "direction": "desc"
                    }
                }
            },
            "query": """query GetBrowseListingQuery($query: SearchQuery) {
  store(browse: true) {
    listing: search(query: $query) {
      resources {
        ...TyItemFragment
        __typename
      }
      __typename
    }
    __typename
  }
  }
fragment TyItemFragment on TyItem {
  id
  slug
  name
  """
            #   title
            #   subtitle
            #   body
            """
  url
  excerpt
  type
  media {
    thumbnail {
      slideshow
      storeSmall
      __typename
    }
    """
            # list {
            #   slideshow
            #   __typename
            # }
            """
    __typename
  }
"""
            #   nativePrice {
            #     amount
            #     discounted
            #     discountDescription
            #     __typename
            #   }
            """
  price {
    amount
    discounted
    taxDescription
    discountDescription
    __typename
  }
  """
            #   stock {
            #     ...TyStockFragment
            #     __typename
            #   }
            #   tags {
            #     ...TyHeapTagFragment
            #     __typename
            #   }
            """
  ... on TySku {
    """
            #    label
            """
    customizable
    isWarbond
    isPackage
    isVip
    isDirectCheckout
    __typename
  }
  ... on TyProduct {
    skus {
      id
      title
      isDirectCheckout
      __typename
    }
    isVip
    __typename
  }
  ... on TyBundle {
    isVip
    media {
      thumbnail {
        slideshow
        __typename
      }
      __typename
    }
    discount {
      ...TyDiscountFragment
      __typename
    }
    __typename
  }
  __typename
  }
fragment TyHeapTagFragment on HeapTag {
  name
  excerpt
  __typename
  }
fragment TyDiscountFragment on TyDiscount {
  id
  title
  skus {
    ...TyBundleSkuFragment
    __typename
  }
  products {
    ...TyBundleProductFragment
    __typename
  }
  __typename
  }
fragment TyBundleSkuFragment on TySku {
  id
  title
  label
  excerpt
  subtitle
  url
  type
  isWarbond
  isDirectCheckout
  media {
    thumbnail {
      storeSmall
      slideshow
      __typename
    }
    __typename
  }
  gameItems {
    __typename
  }
  stock {
    ...TyStockFragment
    __typename
  }
  price {
    amount
    taxDescription
    __typename
  }
  tags {
    ...TyHeapTagFragment
    __typename
  }
  __typename
  }
fragment TyStockFragment on TyStock {
  unlimited
  show
  available
  backOrder
  qty
  backOrderQty
  level
  __typename
  }
fragment TyBundleProductFragment on TyProduct {
  id
  name
  title
  subtitle
  url
  type
  excerpt
  stock {
    ...TyStockFragment
    __typename
  }
  media {
    thumbnail {
      storeSmall
      slideshow
      __typename
    }
    __typename
  }
  nativePrice {
    amount
    discounted
    __typename
  }
  price {
    amount
    discounted
    taxDescription
    __typename
  }
  skus {
    ...TyBundleSkuFragment
    __typename
  }
  __typename
  }
"""
        }
    ]


def send_discord_notification(ships):
    payload = _create_webhook_payload(ships)

    response = urllib.request.urlopen(urllib.request.Request(
        method="POST",
        url=webhook_uri,
        headers={
            'content-type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'
        },
        data=data_to_bytes(payload)
    ))

    return response


def _create_webhook_payload(ships):
    embeds = []
    for ship in ships:
        embeds.append({
            "title": _determine_title(ship),
            "url": _determine_shop_url(ship),
            "color": 5814783,
            "fields": [
                {
                    "name": "Price",
                    "value": _determine_price(ship)
                }
            ],
            "image": {
                "url": _determine_thumbnail_url(ship)
            }
        })
    return {
        "content": _determine_content(),
        "embeds": embeds,
        "attachments": []
    }


def _determine_content():
  message = "The below ships are on sale with Life Time Insurance (LTI).\n_ _"
  if discord_message_mention is not None:
    return f"<@&{discord_message_mention}> {message}"
  return message

def _determine_title(ship):
    if ship is not None and ship['name'] is not None:
        if ship['isWarbond']:
            return f"Warbond {ship['name']}"
        else:
            return ship['name']
    return "Unknown"


def _determine_price(ship):
    if ship is not None and ship['price'] is not None and ship['price']['amount'] is not None:
        return f"${(ship['price']['amount'] / 100):,.2f}"
    return "Unknown"


def _media_url(url):
    if "https://" in url:
        return url
    else:
        # these urls are used for rel links, so if it doesn't include the base we need to assume its from RSI.
        return f"{base_uri}{url}"


def _determine_thumbnail_url(ship):
    if ship is not None and ship['media'] is not None and ship['media']['thumbnail'] is not None and ship['media']['thumbnail']['storeSmall'] is not None:
        url = ship['media']['thumbnail']['storeSmall']
        return _media_url(url=url)
    else:
        return "https://www.google.com/images/errors/robot.png"


def _determine_shop_url(ship):
    if ship is not None and ship['url'] is not None:
        return _media_url(url=ship['url'])
    else:
        return "https://www.google.com/images/errors/robot.png"


def lambda_handler(event, context):
    execute()


if __name__ == "__main__":
    execute()
